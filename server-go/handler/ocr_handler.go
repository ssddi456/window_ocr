package handler

import (
	"net/http"

	"window-ocr/server-go/config"
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
}

// ErrorResponse is returned on failure.
type ErrorResponse struct {
	Success bool   `json:"success"`
	Error   string `json:"error"`
}

// HandleOCR handles POST /api/ocr — accepts base64 image, returns Kimi OCR result.
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
				Error:   "Kimi API key not configured. Please set api_key in config.local.json",
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
		})
	}
}

// HandleHealth returns server health and config status.
func HandleHealth(c *gin.Context) {
	cfg := config.Get()
	hasKey := cfg.Kimi.APIKey != ""
	c.JSON(http.StatusOK, gin.H{
		"status":      "ok",
		"ocr_enabled": hasKey,
		"service":     "window-ocr golang webserver",
	})
}