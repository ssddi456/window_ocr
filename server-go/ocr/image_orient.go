package ocr

import (
	"bytes"
	"image/png"
	"io"

	"github.com/disintegration/imageorient"
)

// decodeWithOrientation reads an image, auto-rotates based on EXIF orientation,
// and returns a re-encoded PNG (always upright, no EXIF metadata).
//
// Supported input formats: JPEG, PNG (others fall through unchanged).
func decodeWithOrientation(r io.Reader, inputFormat string) ([]byte, error) {
	// imageorient.Decode handles JPEG EXIF auto-rotation.
	// For PNG it passes through without rotation (PNG has no EXIF orientation issue).
	img, _, err := imageorient.Decode(r)
	if err != nil {
		return nil, err
	}

	// Re-encode as PNG so Kimi always receives a clean, upright image.
	var buf bytes.Buffer
	if err := png.Encode(&buf, img); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// detectFormat guesses the image format from the first few bytes.
// Returns "jpeg", "png", or "" if unknown.
func detectFormat(raw []byte) string {
	if len(raw) < 4 {
		return ""
	}
	// JPEG: FF D8 FF
	if raw[0] == 0xFF && raw[1] == 0xD8 && raw[2] == 0xFF {
		return "jpeg"
	}
	// PNG: 89 50 4E 47
	if raw[0] == 0x89 && raw[1] == 0x50 && raw[2] == 0x4E && raw[3] == 0x47 {
		return "png"
	}
	return ""
}