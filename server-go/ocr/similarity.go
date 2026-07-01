package ocr

import (
	"image"
	"image/color"
	"math/bits"

	// Register image formats
	_ "image/jpeg"
	_ "image/png"
)

// dHash computes a 64-bit difference hash for perceptual image comparison.
// Steps: resize to 9x8 grayscale, compute row-wise gradients, pack into uint64.
func dHash(img image.Image) uint64 {
	bounds := img.Bounds()
	w, h := bounds.Dx(), bounds.Dy()
	if w == 0 || h == 0 {
		return 0
	}

	// Downscale to 9x8 via nearest-neighbor sampling
	const dw, dh = 9, 8
	var gray [dh][dw]uint8
	for y := 0; y < dh; y++ {
		srcY := y * h / dh
		if srcY >= h {
			srcY = h - 1
		}
		for x := 0; x < dw; x++ {
			srcX := x * w / dw
			if srcX >= w {
				srcX = w - 1
			}
			r, g, b, _ := img.At(srcX, srcY).RGBA()
			// BT.601 luminance
			gray[y][x] = uint8((299*r + 587*g + 114*b) / 1000 / 256)
		}
	}

	// Build hash from horizontal gradients
	var hash uint64
	for y := 0; y < dh; y++ {
		for x := 0; x < dw-1; x++ {
			if gray[y][x] < gray[y][x+1] {
				hash |= 1 << (y*8 + x)
			}
		}
	}
	return hash
}

// hammingDistance returns the number of differing bits between two uint64 values.
func hammingDistance(a, b uint64) int {
	return bits.OnesCount64(a ^ b)
}

// Similarity returns the similarity ratio (0.0–1.0) between two uint64 hashes.
func Similarity(a, b uint64) float64 {
	if a == 0 && b == 0 {
		return 1.0
	}
	return 1.0 - float64(hammingDistance(a, b))/64.0
}

// averageColor returns the average color of an image (simplified).
func averageColor(img image.Image) color.RGBA {
	bounds := img.Bounds()
	var r, g, b, count uint64
	for y := bounds.Min.Y; y < bounds.Max.Y; y++ {
		for x := bounds.Min.X; x < bounds.Max.X; x++ {
			pr, pg, pb, _ := img.At(x, y).RGBA()
			r += uint64(pr)
			g += uint64(pg)
			b += uint64(pb)
			count++
		}
	}
	if count == 0 {
		return color.RGBA{}
	}
	return color.RGBA{
		R: uint8(r / count / 256),
		G: uint8(g / count / 256),
		B: uint8(b / count / 256),
	}
}