package ocr

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image"
	"io"
	"os"
	"strings"
	"time"

	"window-ocr/server-go/config"

	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

// Block represents a single recognized text block.
type Block struct {
	Text string `json:"text"`
}

// OCRResult holds the OCR extraction result.
type OCRResult struct {
	Success  bool    `json:"success"`
	FullText string  `json:"full_text"`
	Blocks   []Block `json:"blocks"`
	Cached   bool    `json:"cached,omitempty"` // true if result came from cache
}

// Engine is the OCR engine with caching and fallback support.
type Engine struct {
	apiKey  string
	baseURL string
	ocrMode string // "auto", "kimi", "wechat"
	client  *openai.Client

	// Cache for exact SHA-256 and perceptual similarity lookups
	cache *Cache

	// WeChat OCR fallback
	wechatOCR *WeChatOCR
}

// NewEngine creates a new OCR engine from current config.
func NewEngine() *Engine {
	cfg := config.Get()
	e := &Engine{
		apiKey:    cfg.Kimi.APIKey,
		baseURL:   cfg.Kimi.BaseURL,
		ocrMode:   cfg.OCRMode,
		cache:     NewCache(10),
		wechatOCR: NewWeChatOCR(""),
	}
	if e.apiKey != "" {
		client := openai.NewClient(
			option.WithAPIKey(e.apiKey),
			option.WithBaseURL(e.baseURL),
		)
		e.client = &client
	}
	return e
}

// ReloadConfig refreshes the engine with latest config.
func (e *Engine) ReloadConfig() {
	cfg := config.Reload()
	e.apiKey = cfg.Kimi.APIKey
	e.baseURL = cfg.Kimi.BaseURL
	e.ocrMode = cfg.OCRMode
	if e.apiKey != "" {
		client := openai.NewClient(
			option.WithAPIKey(e.apiKey),
			option.WithBaseURL(e.baseURL),
		)
		e.client = &client
	} else {
		e.client = nil
	}
}

// Available returns true if any OCR backend is available.
// Respects ocr_mode: "wechat" only needs WeChat, "kimi" only needs Kimi.
func (e *Engine) Available() bool {
	switch e.ocrMode {
	case "wechat":
		return e.wechatOCR.Available()
	case "kimi":
		return e.apiKey != ""
	default: // "auto"
		return e.apiKey != "" || e.wechatOCR.Available()
	}
}

// OCRFromBase64 decodes a base64-encoded image and runs OCR.
//
// Cache lookup order (applies to all modes):
//  1. Exact SHA-256 match
//  2. Perceptual similarity (dHash) among the most recent 10 images (>99%)
//
// OCR backend selection is controlled by config ocr_mode:
//   - "auto":  Kimi first, fallback to WeChat OCR on failure
//   - "kimi":  Kimi only, error if unavailable or fails
//   - "wechat": WeChat OCR only, error if unavailable
func (e *Engine) OCRFromBase64(ctx context.Context, b64Data string) (*OCRResult, error) {
	// Strip data URI prefix if present
	b64Data = stripDataURIPrefix(b64Data)

	// Decode base64
	raw, err := base64.StdEncoding.DecodeString(b64Data)
	if err != nil {
		return nil, fmt.Errorf("base64 decode failed: %w", err)
	}

	// Auto-rotate based on EXIF orientation
	imgFormat := detectFormat(raw)
	if imgFormat != "" {
		corrected, err := decodeWithOrientation(bytes.NewReader(raw), imgFormat)
		if err == nil {
			raw = corrected
		}
	}

	// ---- Cache lookups (shared by all modes) ----

	// 1. Exact SHA-256 match
	hash := SHA256Hash(raw)
	if cached := e.cache.Lookup(hash); cached != nil {
		result := *cached
		result.Cached = true
		return &result, nil
	}

	// 2. Perceptual similarity (dHash) among recent 10
	img, _, err := image.Decode(bytes.NewReader(raw))
	if err == nil {
		dh := dHash(img)
		if cached := e.cache.LookupSimilarity(dh); cached != nil {
			result := *cached
			result.Cached = true
			return &result, nil
		}
	}

	// ---- Call OCR based on mode ----

	var result *OCRResult
	switch e.ocrMode {
	case "wechat":
		result, err = e.callWechatOnly(ctx, img)
	case "kimi":
		result, err = e.callKimiOnly(ctx, raw)
	default: // "auto"
		result, err = e.callAuto(ctx, raw, img)
	}

	if err != nil {
		return nil, err
	}

	// Store in cache
	if img != nil {
		e.cache.Store(hash, dHash(img), result)
	} else {
		e.cache.Store(hash, 0, result)
	}

	return result, nil
}

// callAuto implements "auto" mode: Kimi first, WeChat fallback.
func (e *Engine) callAuto(ctx context.Context, raw []byte, img image.Image) (*OCRResult, error) {
	result, err := e.callKimiOCR(ctx, raw)
	if err != nil {
		if img != nil && e.wechatOCR.Available() {
			return e.wechatOCR.OCRFromImage(ctx, img)
		}
		return nil, err
	}
	return result, nil
}

// callKimiOnly implements "kimi" mode: Kimi only, no fallback.
func (e *Engine) callKimiOnly(ctx context.Context, raw []byte) (*OCRResult, error) {
	return e.callKimiOCR(ctx, raw)
}

// callWechatOnly implements "wechat" mode: WeChat OCR only.
func (e *Engine) callWechatOnly(ctx context.Context, img image.Image) (*OCRResult, error) {
	if img == nil {
		return nil, fmt.Errorf("wechat OCR: failed to decode image")
	}
	if !e.wechatOCR.Available() {
		return nil, fmt.Errorf("wechat OCR not available")
	}
	return e.wechatOCR.OCRFromImage(ctx, img)
}

// callKimiOCR writes raw image bytes to a temp file, calls Kimi API,
// and deletes the temp file immediately after the API call completes.
func (e *Engine) callKimiOCR(ctx context.Context, raw []byte) (*OCRResult, error) {
	if e.apiKey == "" {
		return nil, fmt.Errorf("Kimi API key not configured")
	}

	tmpDir := os.TempDir()
	tmpFile, err := os.CreateTemp(tmpDir, "ocr_*.png")
	if err != nil {
		return nil, fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmpFile.Name()
	defer os.Remove(tmpPath) // clean up temp file after OCR completes

	if _, err := tmpFile.Write(raw); err != nil {
		tmpFile.Close()
		return nil, fmt.Errorf("write temp file: %w", err)
	}
	tmpFile.Close()

	return e.OCR(ctx, tmpPath)
}

// OCR uploads an image file to Kimi file-extract API and returns recognized text.
func (e *Engine) OCR(ctx context.Context, imagePath string) (*OCRResult, error) {
	if e.apiKey == "" {
		return nil, fmt.Errorf("Kimi API key not configured")
	}

	f, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("image file not found: %w", err)
	}
	defer f.Close()

	if e.client == nil {
		return nil, fmt.Errorf("Kimi API client not initialized")
	}
	fileObj, err := e.client.Files.New(ctx, openai.FileNewParams{
		File:    f,
		Purpose: openai.FilePurpose("file-extract"),
	})
	if err != nil {
		return nil, fmt.Errorf("Kimi file upload failed: %w", err)
	}
	// Delete the remote file on Kimi's server after OCR completes
	defer func() {
		_, _ = e.client.Files.Delete(ctx, fileObj.ID)
	}()

	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}

	resp, err := e.client.Files.Content(ctx, fileObj.ID)
	if err != nil {
		return nil, fmt.Errorf("Kimi file content retrieval failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("Kimi file content read failed: %w", err)
	}

	fullText := string(body)
	var data struct {
		Content  string `json:"content"`
		FileType string `json:"file_type"`
	}
	if json.Unmarshal(body, &data) == nil && data.Content != "" {
		fullText = data.Content
	}

	lines := strings.Split(fullText, "\n")
	var blocks []Block
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" {
			blocks = append(blocks, Block{Text: trimmed})
		}
	}

	return &OCRResult{
		Success:  true,
		FullText: fullText,
		Blocks:   blocks,
	}, nil
}

// stripDataURIPrefix removes "data:image/...;base64," prefix if present.
func stripDataURIPrefix(s string) string {
	if idx := strings.Index(s, ","); idx >= 0 && strings.HasPrefix(s, "data:") {
		return s[idx+1:]
	}
	return s
}