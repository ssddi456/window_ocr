package ocr

import (
	"context"
	"encoding/base64"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestStripDataURIPrefix_WithPrefix(t *testing.T) {
	input := "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA"
	got := stripDataURIPrefix(input)
	expected := "iVBORw0KGgoAAAANSUhEUgAA"
	if got != expected {
		t.Errorf("expected %q, got %q", expected, got)
	}
}

func TestStripDataURIPrefix_WithoutPrefix(t *testing.T) {
	input := "iVBORw0KGgoAAAANSUhEUgAA"
	got := stripDataURIPrefix(input)
	if got != input {
		t.Errorf("expected unchanged %q, got %q", input, got)
	}
}

func TestStripDataURIPrefix_Empty(t *testing.T) {
	got := stripDataURIPrefix("")
	if got != "" {
		t.Errorf("expected empty, got %q", got)
	}
}

func TestStripDataURIPrefix_NoComma(t *testing.T) {
	input := "data:image/png;base64"
	got := stripDataURIPrefix(input)
	if got != input {
		t.Errorf("expected unchanged %q, got %q", input, got)
	}
}

func TestEngine_Available_NoAPIKey(t *testing.T) {
	eng := &Engine{apiKey: ""}
	if eng.Available() {
		t.Errorf("expected Available=false when apiKey is empty")
	}
}

func TestEngine_Available_WithAPIKey(t *testing.T) {
	eng := &Engine{apiKey: "some-key"}
	if !eng.Available() {
		t.Errorf("expected Available=true when apiKey is set")
	}
}

func TestOCRResult_Struct(t *testing.T) {
	r := OCRResult{
		Success:  true,
		FullText: "hello\nworld",
		Blocks: []Block{
			{Text: "hello"},
			{Text: "world"},
		},
	}
	if !r.Success {
		t.Errorf("expected Success=true")
	}
	if r.FullText != "hello\nworld" {
		t.Errorf("expected FullText 'hello\\nworld', got %q", r.FullText)
	}
	if len(r.Blocks) != 2 {
		t.Errorf("expected 2 blocks, got %d", len(r.Blocks))
	}
}

func TestOCRFromBase64_EngineNotAvailable(t *testing.T) {
	eng := &Engine{apiKey: ""}
	_, err := eng.OCRFromBase64(context.Background(), "dGVzdA==")
	if err == nil {
		t.Fatal("expected error when engine not available")
	}
	if !strings.Contains(err.Error(), "not configured") {
		t.Errorf("expected 'not configured' in error, got %s", err.Error())
	}
}

func TestOCRFromBase64_InvalidBase64(t *testing.T) {
	eng := &Engine{apiKey: "test-key"}
	_, err := eng.OCRFromBase64(context.Background(), "not-valid-base64!!!")
	if err == nil {
		t.Fatal("expected error for invalid base64")
	}
	if !strings.Contains(err.Error(), "base64 decode failed") {
		t.Errorf("expected 'base64 decode failed', got %s", err.Error())
	}
}

func TestOCRFromBase64_NilClient(t *testing.T) {
	// Engine with API key but no client (simulates config set but client not initialized)
	eng := &Engine{apiKey: "test-key", client: nil}

	pngData := base64.StdEncoding.EncodeToString([]byte{
		0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
		0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
		0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
		0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
		0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
		0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
		0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
	})

	_, err := eng.OCRFromBase64(context.Background(), pngData)
	if err == nil {
		t.Fatal("expected error when client is nil")
	}
	if !strings.Contains(err.Error(), "client not initialized") {
		t.Errorf("expected 'client not initialized' error, got: %s", err.Error())
	}
}

func TestOCR_FileNotFound(t *testing.T) {
	eng := &Engine{apiKey: "test-key"}
	_, err := eng.OCR(context.Background(), filepath.Join(os.TempDir(), "nonexistent_ocr_test_file.png"))
	if err == nil {
		t.Fatal("expected error for missing file")
	}
	if !strings.Contains(err.Error(), "not found") {
		t.Errorf("expected 'not found' error, got %s", err.Error())
	}
}

func TestOCR_EngineNotAvailable(t *testing.T) {
	eng := &Engine{apiKey: ""}
	_, err := eng.OCR(context.Background(), "/some/file.png")
	if err == nil {
		t.Fatal("expected error when engine not available")
	}
}

func TestReloadConfig(t *testing.T) {
	eng := &Engine{apiKey: ""}
	if eng.Available() {
		t.Fatal("expected empty engine to be unavailable")
	}
	eng.ReloadConfig()
	if eng.Available() {
		t.Errorf("expected engine to remain unavailable after reload with no config")
	}
}