package ocr

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
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
}

// Engine is the Kimi OCR engine using file-extract API.
type Engine struct {
	apiKey  string
	baseURL string
	client  *openai.Client
}

// NewEngine creates a new OCR engine from current config.
func NewEngine() *Engine {
	cfg := config.Get()
	e := &Engine{
		apiKey:  cfg.Kimi.APIKey,
		baseURL: cfg.Kimi.BaseURL,
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

// Available returns true if API key is configured.
func (e *Engine) Available() bool {
	return e.apiKey != ""
}

// OCRFromBase64 decodes a base64-encoded image and runs OCR via Kimi file-extract API.
// The base64 string may include the data URI prefix (e.g. "data:image/png;base64,").
func (e *Engine) OCRFromBase64(ctx context.Context, b64Data string) (*OCRResult, error) {
	if !e.Available() {
		return nil, fmt.Errorf("Kimi API key not configured")
	}

	// Strip data URI prefix if present
	b64Data = stripDataURIPrefix(b64Data)

	// Decode base64
	raw, err := base64.StdEncoding.DecodeString(b64Data)
	if err != nil {
		return nil, fmt.Errorf("base64 decode failed: %w", err)
	}

	// Auto-rotate based on EXIF orientation (fixes portrait photos)
	imgFormat := detectFormat(raw)
	if imgFormat != "" {
		corrected, err := decodeWithOrientation(bytes.NewReader(raw), imgFormat)
		if err == nil {
			raw = corrected
		}
		// On failure, fall through with original raw bytes
	}

	// Write to temp file
	tmpDir := os.TempDir()
	tmpFile, err := os.CreateTemp(tmpDir, "ocr_*.png")
	if err != nil {
		return nil, fmt.Errorf("create temp file: %w", err)
	}
	tmpPath := tmpFile.Name()
	defer os.Remove(tmpPath)

	if _, err := tmpFile.Write(raw); err != nil {
		tmpFile.Close()
		return nil, fmt.Errorf("write temp file: %w", err)
	}
	tmpFile.Close()

	// Call OCR
	return e.OCR(ctx, tmpPath)
}

// OCR uploads an image file to Kimi file-extract API and returns recognized text.
func (e *Engine) OCR(ctx context.Context, imagePath string) (*OCRResult, error) {
	if !e.Available() {
		return nil, fmt.Errorf("Kimi API key not configured")
	}

	// Open file for upload
	f, err := os.Open(imagePath)
	if err != nil {
		return nil, fmt.Errorf("image file not found: %w", err)
	}
	defer f.Close()

	// Upload file with file-extract purpose
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

	// Wait a moment for processing (Kimi may need time)
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(500 * time.Millisecond):
	}

	// Retrieve file content
	resp, err := e.client.Files.Content(ctx, fileObj.ID)
	if err != nil {
		return nil, fmt.Errorf("Kimi file content retrieval failed: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("Kimi file content read failed: %w", err)
	}

	// Parse response
	fullText := string(body)
	var data struct {
		Content  string `json:"content"`
		FileType string `json:"file_type"`
	}
	if json.Unmarshal(body, &data) == nil && data.Content != "" {
		fullText = data.Content
	}

	// Split into non-empty lines as blocks
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