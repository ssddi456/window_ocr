package ocr

import (
	"crypto/sha256"
	"encoding/hex"
	"sync"
)

// CachedResult stores a cached OCR result with metadata.
type CachedResult struct {
	Hash     string  // SHA-256 hash of raw image bytes
	DH       uint64  // dHash for perceptual similarity matching
	FullText string
	Blocks   []Block
}

// Cache stores up to maxEntries recent OCR results, keyed by SHA-256 hash.
// Also maintains a ring buffer for perceptual similarity lookups.
type Cache struct {
	mu      sync.RWMutex
	maxSize int
	entries []CachedResult // newest first ring buffer
	byHash  map[string]*OCRResult
}

// NewCache creates a cache with the given maximum number of entries.
func NewCache(maxSize int) *Cache {
	return &Cache{
		maxSize: maxSize,
		entries: make([]CachedResult, 0, maxSize),
		byHash:  make(map[string]*OCRResult),
	}
}

// SHA256Hash computes the hex-encoded SHA-256 digest of raw bytes.
func SHA256Hash(raw []byte) string {
	h := sha256.Sum256(raw)
	return hex.EncodeToString(h[:])
}

// Lookup returns a cached OCR result by exact SHA-256 hash.
func (c *Cache) Lookup(hash string) *OCRResult {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.byHash[hash]
}

// LookupSimilarity searches the recent entries for a dHash match with
// similarity > 99% (hamming distance 0). Returns the matching result or nil.
func (c *Cache) LookupSimilarity(dh uint64) *OCRResult {
	c.mu.RLock()
	defer c.mu.RUnlock()
	for _, entry := range c.entries {
		if hammingDistance(entry.DH, dh) == 0 {
			return c.byHash[entry.Hash]
		}
	}
	return nil
}

// Store saves an OCR result in the cache.
func (c *Cache) Store(hash string, dh uint64, result *OCRResult) {
	c.mu.Lock()
	defer c.mu.Unlock()

	// Update map
	c.byHash[hash] = result

	// Prepend to ring buffer
	entry := CachedResult{
		Hash:     hash,
		DH:       dh,
		FullText: result.FullText,
		Blocks:   result.Blocks,
	}
	c.entries = append([]CachedResult{entry}, c.entries...)
	if len(c.entries) > c.maxSize {
		// Remove oldest
		oldest := c.entries[len(c.entries)-1]
		delete(c.byHash, oldest.Hash)
		c.entries = c.entries[:c.maxSize]
	}
}

// Size returns the number of entries currently in the cache.
func (c *Cache) Size() int {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return len(c.entries)
}