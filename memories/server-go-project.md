# server-go 项目记忆

## 环境
- 运行环境：Windows，使用 PowerShell
- Go 版本：1.25.0
- 模块路径：window-ocr/server-go

## 依赖
- Web 框架：github.com/gin-gonic/gin v1.12.0
- Kimi OCR：github.com/openai/openai-go v1.12.0（兼容 Kimi API）
  - 版本号必须是 v0 或 v1，不能使用 v3 等无效版本

## 项目结构
- config/ — 配置管理（config.json + config.local.json 深度合并）
- handler/ — HTTP 处理器（健康检查、OCR 接口）
- ocr/ — Kimi OCR 引擎（base64 解码、文件上传、内容提取）
- main.go — 入口，Gin 路由 + 优雅关闭

## API
- GET /health — 健康检查
- POST /api/ocr — 接收 {image_base64: string}，返回 OCR 结果

## 测试
- config 包：4 个测试（默认值、Get/Set 线程安全、并发读、Load Once）
- handler 包：7 个测试（健康检查、OCR 各状态码路径）
- ocr 包：9 个测试（stripDataURIPrefix、Available、OCRFromBase64 错误路径、nil client 防护）
- 手动测试页面：test-ocr.html（支持拖拽和 Ctrl+V 粘贴图片）

## 关键修复
- go.mod 中 openai-go 版本从无效 v3.41.0 降级为合法 v1.12.0
- ocr/engine.go 适配 openai-go v1 API：
  - NewClient 返回值类型改为值类型（取地址存储）
  - Files.New 参数 File 类型为 io.Reader
  - Files.Content 返回 *http.Response，需读取 Body
  - 添加 nil client 防护检查