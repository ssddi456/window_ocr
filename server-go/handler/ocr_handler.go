package handler

import (
	"net/http"

	"window-ocr/server-go/ocr"

	"github.com/gin-gonic/gin"
)

// OCRRequest is the expected JSON body for the OCR endpoint.
type OCRRequest struct {
	ImageBase64 string `json:"image_base64" binding:"required"`
}

// OCRResponse is returned on success.
type OCRResponse struct {
	Success  bool        `json:"success"`
	FullText string      `json:"full_text"`
	Blocks   []ocr.Block `json:"blocks"`
	Cached   bool        `json:"cached,omitempty"`
}

// ErrorResponse is returned on failure.
type ErrorResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

// HandleOCR handles POST /api/ocr — accepts base64 image, returns OCR result
// with caching and Kimi → WeChat OCR fallback.
func HandleOCR(engine *ocr.Engine) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req OCRRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, ErrorResponse{
				Success: false,
				Error:   "invalid request: " + err.Error(),
			})
			return
		}

		if !engine.Available() {
			c.JSON(http.StatusServiceUnavailable, ErrorResponse{
				Success: false,
				Error:   "No OCR backend available. Configure Kimi API key or install wechat-ocr-go.",
			})
			return
		}

		result, err := engine.OCRFromBase64(c.Request.Context(), req.ImageBase64)
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
			Cached:   result.Cached,
		})
	}
}

// HandleHealth returns server health and config status.
func HandleHealth(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":      "ok",
		"service":     "window-ocr golang webserver",
		"ocr_enabled": true, // always true since WeChat OCR fallback may be available
	})
}