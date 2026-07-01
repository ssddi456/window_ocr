---
brief: OCR缓存、降级逻辑和模式配置架构
---

## OCR 模式配置 (`config.json` → `ocr_mode`)
- `"auto"`（默认）：Kimi 优先，失败时降级到 WeChat OCR
- `"kimi"`：仅使用 Kimi API，不降级
- `"wechat"`：仅使用 WeChat OCR
- 配置文件：`config.json` 和 `config.local.json` 均支持覆盖此字段

## 缓存机制
- **SHA-256** 精确匹配：首次请求时计算图片哈希，后续相同图片直接返回缓存
- **dHash 感知相似度**：最近10张图片中，hamming距离=0（99%+相似度）视为相同，直接返回缓存
- 缓存命中时返回 `cached: true`，节省API调用

## 降级链（仅 auto 模式）
1. Kimi API (file-extract) → 失败时
2. WeChat OCR (fanchenggang/wechat-ocr-go) 作为 fallback

## 临时文件清理
- Kimi API 调用创建临时 PNG 文件于系统临时目录
- `defer os.Remove()` 确保 API 调用完成后（成功或失败）立即删除临时文件

## 模块
- `ocr/cache.go` - 缓存存储（SHA-256 + 环缓冲区）
- `ocr/similarity.go` - dHash 和 hamming distance 计算
- `ocr/wechat_ocr.go` - WeChat OCR 命令行调用
- `ocr/engine.go` - 集成缓存查找、模式路由和 fallback
- `handler/ocr_handler.go` - API 层适配
- `config/config.go` - 配置加载，含 OCRMode 字段