package handler

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"window-ocr/server-go/config"
	"window-ocr/server-go/ocr"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// mockEngine is a simple mock that controls Available() and OCRFromBase64 behavior.
type mockEngine struct {
	available bool
	ocrResult *ocr.OCRResult
	ocrErr    error
}

func (m *mockEngine) Available() bool { return m.available }
func (m *mockEngine) OCRFromBase64(ctx interface{}, b64 string) (*ocr.OCRResult, error) {
	return m.ocrResult, m.ocrErr
}

// setupRouter creates a test router with the HandleOCR logic inlined using the mock.
func setupRouter(eng *mockEngine) *gin.Engine {
	r := gin.New()
	r.GET("/health", HandleHealth)
	r.POST("/api/ocr", func(c *gin.Context) {
		var req OCRRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{
				Success: false,
				Error:   "invalid request: " + err.Error(),
			})
			return
		}
		if !eng.Available() {
			c.JSON(http.StatusServiceUnavailable, ErrorResponse{
				Success: false,
				Error:   "Kimi API key not configured. Please set api_key in config.local.json",
			})
			return
		}
		result, err := eng.OCRFromBase64(nil, req.ImageBase64)
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{
				Success: false,
				Error:   err.Error(),
			})
			return
		}
		c.JSON(http.StatusOK, OCRResponse{
			Success:  result.Success,
			FullText: result.FullText,
			Blocks:   result.Blocks,
		})
	})
	return r
}

func TestHandleHealth(t *testing.T) {
	config.Set(config.AppConfig{
		Kimi: config.KimiConfig{APIKey: "test-key"},
		Port: 8618,
	})

	r := gin.New()
	r.GET("/health", HandleHealth)
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)

	if body["status"] != "ok" {
		t.Errorf("expected status 'ok', got %v", body["status"])
	}
	if body["ocr_enabled"] != true {
		t.Errorf("expected ocr_enabled=true when API key is set, got %v", body["ocr_enabled"])
	}
}

func TestHandleHealth_OCRDisabled(t *testing.T) {
	config.Set(config.AppConfig{
		Kimi: config.KimiConfig{APIKey: ""},
		Port: 8618,
	})

	r := gin.New()
	r.GET("/health", HandleHealth)
	req := httptest.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var body map[string]interface{}
	json.Unmarshal(w.Body.Bytes(), &body)

	if body["ocr_enabled"] != false {
		t.Errorf("expected ocr_enabled=false without API key, got %v", body["ocr_enabled"])
	}
}

func TestHandleOCR_MissingBody(t *testing.T) {
	eng := &mockEngine{available: true}
	r := setupRouter(eng)

	req := httptest.NewRequest("POST", "/api/ocr", strings.NewReader("not json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400, got %d", w.Code)
	}
}

func TestHandleOCR_EmptyImageBase64(t *testing.T) {
	eng := &mockEngine{available: true}
	r := setupRouter(eng)

	body := `{"image_base64":""}`
	req := httptest.NewRequest("POST", "/api/ocr", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	// Gin's "required" binding treats empty string as missing value → 400
	if w.Code != http.StatusBadRequest {
		t.Errorf("expected status 400 for empty image_base64 (required field), got %d", w.Code)
	}
}

func TestHandleOCR_EngineNotAvailable(t *testing.T) {
	eng := &mockEngine{available: false}
	r := setupRouter(eng)

	body := `{"image_base64":"aW1hZ2VkYXRh"}`
	req := httptest.NewRequest("POST", "/api/ocr", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusServiceUnavailable {
		t.Errorf("expected status 503, got %d", w.Code)
	}

	var errResp ErrorResponse
	json.Unmarshal(w.Body.Bytes(), &errResp)
	if errResp.Success != false {
		t.Errorf("expected success=false")
	}
}

func TestHandleOCR_Success(t *testing.T) {
	eng := &mockEngine{
		available: true,
		ocrResult: &ocr.OCRResult{
			Success:  true,
			FullText: "Hello World",
			Blocks:   []ocr.Block{{Text: "Hello World"}},
		},
	}
	r := setupRouter(eng)

	body := `{"image_base64":"aW1hZ2VkYXRh"}`
	req := httptest.NewRequest("POST", "/api/ocr", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("expected status 200, got %d", w.Code)
	}

	var resp OCRResponse
	json.Unmarshal(w.Body.Bytes(), &resp)
	if !resp.Success {
		t.Errorf("expected success=true")
	}
	if resp.FullText != "Hello World" {
		t.Errorf("expected FullText 'Hello World', got %s", resp.FullText)
	}
	if len(resp.Blocks) != 1 || resp.Blocks[0].Text != "Hello World" {
		t.Errorf("expected 1 block with text 'Hello World', got %+v", resp.Blocks)
	}
}

func TestHandleOCR_EngineError(t *testing.T) {
	eng := &mockEngine{
		available: true,
		ocrErr:    &mockError{msg: "OCR processing failed"},
	}
	r := setupRouter(eng)

	body := `{"image_base64":"aW1hZ2VkYXRh"}`
	req := httptest.NewRequest("POST", "/api/ocr", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Errorf("expected status 500, got %d", w.Code)
	}

	var errResp ErrorResponse
	json.Unmarshal(w.Body.Bytes(), &errResp)
	if errResp.Error != "OCR processing failed" {
		t.Errorf("expected error message 'OCR processing failed', got %s", errResp.Error)
	}
}

type mockError struct{ msg string }

func (e *mockError) Error() string { return e.msg }