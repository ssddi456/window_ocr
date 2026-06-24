# POST /api/ocr — 图片 OCR 识别

> **基础地址**: `http://localhost:8618`  
> **协议**: HTTP/1.1, JSON

---

将 Base64 编码的图片发送给 Kimi 模型进行 OCR 文字识别。

**请求头：**

```
Content-Type: application/json
```

**请求体：**

```json
{
  "image_base64": "iVBORw0KGgo...（Base64 编码的图片数据）"
}
```

| 参数           | 类型   | 必填 | 说明                                                        |
|----------------|--------|:---:|-------------------------------------------------------------|
| `image_base64` | string | ✓   | 图片的 Base64 编码字符串，可包含 `data:image/...;base64,` 前缀 |

**支持格式**: PNG / JPEG / GIF / BMP / WebP

---

### 成功响应 (200)

```json
{
  "success": true,
  "full_text": "识别的完整文本内容\n换行保留",
  "blocks": [
    { "text": "第一行文本" },
    { "text": "第二行文本" }
  ]
}
```

| 字段             | 类型    | 说明                        |
|------------------|---------|-----------------------------|
| `success`        | boolean | `true` 表示识别成功         |
| `full_text`      | string  | Kimi 返回的完整 OCR 文本    |
| `blocks`         | array   | 按行拆分后的非空文本块数组  |
| `blocks[].text`  | string  | 单行文本内容                |

---

### 错误响应

**400 — 请求格式错误**

```json
{
  "success": false,
  "error": "invalid request: ..."
}
```

**503 — 未配置 API Key**

```json
{
  "success": false,
  "error": "Kimi API key not configured. Please set api_key in config.local.json"
}
```

**500 — Kimi API 调用失败**

```json
{
  "success": false,
  "error": "具体错误信息"
}
```

---

## 调用示例

### cURL

```bash
BASE64=$(base64 -w 0 screenshot.png)
curl -X POST http://localhost:8618/api/ocr \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$BASE64\"}"
```

### PowerShell

```powershell
$base64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("screenshot.png"))
$body = @{ image_base64 = $base64 } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8618/api/ocr -Method Post -Body $body -ContentType "application/json"
```

### JavaScript

```javascript
const file = document.querySelector('input[type=file]').files[0];
const reader = new FileReader();
reader.onload = async () => {
  const image_base64 = reader.result.split(',')[1];
  const res = await fetch('http://localhost:8618/api/ocr', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_base64 })
  });
  const data = await res.json();
  console.log(data.full_text);
};
reader.readAsDataURL(file);
```

### Python

```python
import base64, requests

with open("screenshot.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

resp = requests.post(
    "http://localhost:8618/api/ocr",
    json={"image_base64": b64}
)
print(resp.json()["full_text"])
```

---

## 配置说明

在项目根目录创建 `config.local.json` 配置 Kimi API Key：

```json
{
  "kimi": {
    "api_key": "sk-your-kimi-api-key-here"
  }
}
```