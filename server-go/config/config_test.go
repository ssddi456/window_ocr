package config

import (
	"sync"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()
	if cfg.Port != 8618 {
		t.Errorf("expected default port 8618, got %d", cfg.Port)
	}
	if cfg.Kimi.BaseURL != "https://api.moonshot.cn/v1" {
		t.Errorf("expected default base URL, got %s", cfg.Kimi.BaseURL)
	}
	if cfg.Kimi.APIKey != "" {
		t.Errorf("expected empty API key by default, got %s", cfg.Kimi.APIKey)
	}
}

func TestGetSet_ThreadSafe(t *testing.T) {
	cfg := AppConfig{
		Kimi: KimiConfig{APIKey: "test-key", BaseURL: "https://test.com/v1"},
		Port: 9999,
	}
	Set(cfg)
	got := Get()
	if got.Kimi.APIKey != "test-key" {
		t.Errorf("expected API key 'test-key', got %s", got.Kimi.APIKey)
	}
	if got.Port != 9999 {
		t.Errorf("expected port 9999, got %d", got.Port)
	}

	// Reset to default to clean up global state
	Set(DefaultConfig())
}

func TestGetSet_ConcurrentRead(t *testing.T) {
	cfg := AppConfig{
		Kimi: KimiConfig{APIKey: "concurrent-key"},
		Port: 8888,
	}
	Set(cfg)

	done := make(chan bool, 10)
	for i := 0; i < 10; i++ {
		go func() {
			g := Get()
			if g.Kimi.APIKey != "concurrent-key" {
				t.Errorf("concurrent read: expected 'concurrent-key', got %s", g.Kimi.APIKey)
			}
			done <- true
		}()
	}
	for i := 0; i < 10; i++ {
		<-done
	}

	Set(DefaultConfig())
}

func TestLoad_OnceBehavior(t *testing.T) {
	// Reset once to test Load behavior
	mu.Lock()
	once = sync.Once{}
	globalCfg = AppConfig{}
	mu.Unlock()

	// Load should use default config since no config files are present in test environment
	cfg := Load()
	if cfg.Port != 8618 {
		t.Errorf("expected port 8618 (default), got %d", cfg.Port)
	}

	// Second call should return same config (due to sync.Once)
	cfg2 := Load()
	if cfg2.Port != cfg.Port {
		t.Errorf("expected same config, got different")
	}
}