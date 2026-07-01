package ocr

import (
	"bytes"
	"context"
	"fmt"
	"image"
	"image/png"
	"os/exec"
	"time"
)

// WeChatOCR provides OCR using the WeChat OCR engine via command line.
// Uses fanchenggang/wechat-ocr-go as an executable wrapper.
type WeChatOCR struct {
	execPath string
	timeout  time.Duration
}

// NewWeChatOCR creates a new WeChat OCR engine.
// execPath is the path to the wechat-ocr-go binary.
func NewWeChatOCR(execPath string) *WeChatOCR {
	if execPath == "" {
		execPath = "wechat-ocr-go"
	}
	return &WeChatOCR{
		execPath: execPath,
		timeout:  30 * time.Second,
	}
}

// Available returns true if the WeChat OCR executable is found.
func (w *WeChatOCR) Available() bool {
	_, err := exec.LookPath(w.execPath)
	return err == nil
}

// OCRFromImage runs WeChat OCR on the given image bytes.
func (w *WeChatOCR) OCRFromImage(ctx context.Context, img image.Image) (*OCRResult, error) {
	if !w.Available() {
		return nil, fmt.Errorf("wechat-ocr-go executable not found")
	}

	// Encode image to PNG in memory
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return nil, fmt.Errorf("failed to encode image for WeChat OCR: %w", err)
	}

	// WeChat OCR reads from stdin and writes JSON to stdout
	ctx, cancel := context.WithTimeout(ctx, w.timeout)
	defer cancel()

	cmd := exec.CommandContext(ctx, w.execPath)
	cmd.Stdin = &buf

	stdout, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("wechat-ocr-go failed: %w", err)
	}

	// Parse output: expected JSON with "text" field
	fullText := string(stdout)

	// Split into non-empty lines as blocks
	lines := bytes.Split(bytes.TrimSpace(stdout), []byte("\n"))
	var blocks []Block
	for _, line := range lines {
		trimmed := bytes.TrimSpace(line)
		if len(trimmed) > 0 {
			blocks = append(blocks, Block{Text: string(trimmed)})
		}
	}

	return &OCRResult{
		Success:  true,
		FullText: fullText,
		Blocks:   blocks,
	}, nil
}