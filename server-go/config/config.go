package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// KimiConfig holds Kimi API settings.
type KimiConfig struct {
	APIKey  string `json:"api_key"`
	BaseURL string `json:"base_url"`
}

// AppConfig is the top-level application config.
type AppConfig struct {
	Kimi    KimiConfig `json:"kimi"`
	Port    int        `json:"port"`     // server listen port, default 8618
	OCRMode string     `json:"ocr_mode"` // "auto" (default), "kimi", "wechat"
}

var (
	globalCfg AppConfig
	once      sync.Once
	mu        sync.RWMutex
)

// DefaultConfig returns config with sensible defaults.
func DefaultConfig() AppConfig {
	return AppConfig{
		Kimi: KimiConfig{
			BaseURL: "https://api.moonshot.cn/v1",
		},
		Port:    8618,
		OCRMode: "auto",
	}
}

// Load reads config.json and config.local.json (if exists) from parent project root.
// config.local.json values override config.json values (deep merge for maps).
func Load() AppConfig {
	once.Do(func() {
		globalCfg = loadConfig()
	})
	return globalCfg
}

// Reload forces a fresh read of config files.
func Reload() AppConfig {
	mu.Lock()
	defer mu.Unlock()
	globalCfg = loadConfig()
	return globalCfg
}

// Get returns the current global config (thread-safe).
func Get() AppConfig {
	mu.RLock()
	defer mu.RUnlock()
	return globalCfg
}

// Set updates the global config (thread-safe).
func Set(cfg AppConfig) {
	mu.Lock()
	defer mu.Unlock()
	globalCfg = cfg
}

func loadConfig() AppConfig {
	cfg := DefaultConfig()

	// Determine project root (parent of server-go/)
	execPath, err := os.Executable()
	if err != nil {
		execPath, _ = os.Getwd()
	}
	serverDir := filepath.Dir(execPath)
	// If running from source (go run), executable is in temp dir; fall back to CWD.
	if _, err := os.Stat(filepath.Join(serverDir, "..", "config.json")); os.IsNotExist(err) {
		cwd, _ := os.Getwd()
		// cwd may be server-go/ itself, so try parent
		if _, err := os.Stat(filepath.Join(cwd, "config.json")); err == nil {
			serverDir = cwd
		} else if _, err := os.Stat(filepath.Join(cwd, "..", "config.json")); err == nil {
			serverDir = filepath.Dir(cwd)
		}
	}

	projectRoot := filepath.Dir(serverDir)
	configPath := filepath.Join(projectRoot, "config.json")
	localPath := filepath.Join(projectRoot, "config.local.json")

	// Read config.json
	if data, err := os.ReadFile(configPath); err == nil {
		var base AppConfig
		if json.Unmarshal(data, &base) == nil {
			cfg.Kimi = base.Kimi
			if base.Port > 0 {
				cfg.Port = base.Port
			}
			if base.OCRMode != "" {
				cfg.OCRMode = base.OCRMode
			}
		}
	}

	// Merge config.local.json
	if data, err := os.ReadFile(localPath); err == nil {
		var local AppConfig
		if json.Unmarshal(data, &local) == nil {
			if local.Kimi.APIKey != "" {
				cfg.Kimi.APIKey = local.Kimi.APIKey
			}
			if local.Kimi.BaseURL != "" {
				cfg.Kimi.BaseURL = local.Kimi.BaseURL
			}
			if local.Port > 0 {
				cfg.Port = local.Port
			}
			if local.OCRMode != "" {
				cfg.OCRMode = local.OCRMode
			}
		}
	}

	return cfg
}