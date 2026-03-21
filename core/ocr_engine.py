"""OCR engine — uses Kimi (Moonshot) file-extract API for image recognition."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = CONFIG_DIR / "config.json"
CONFIG_LOCAL_PATH = CONFIG_DIR / "config.local.json"


def load_config() -> dict:
    """Load config, merging config.local.json over config.json."""
    cfg: dict = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    if CONFIG_LOCAL_PATH.exists():
        try:
            with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
                local = json.load(f)
            for k, v in local.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception:
            pass
    return cfg


def save_config(cfg: dict) -> None:
    """Save config to config.local.json (keeps secrets out of config.json)."""
    with open(CONFIG_LOCAL_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


class OCREngine:
    """OCR via Kimi (Moonshot) file-extract API.

    Uses the OpenAI-compatible SDK to upload images and extract text.
    API key is stored in config.local.json for security.
    """

    def __init__(self) -> None:
        self._client = None
        self._api_key: str = ""
        self._base_url: str = ""
        self.reload_config()

    def reload_config(self) -> None:
        cfg = load_config()
        kimi = cfg.get("kimi", {})
        self._api_key = kimi.get("api_key", "")
        self._base_url = kimi.get("base_url", "https://api.moonshot.cn/v1")
        self._client = None  # reset

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        return self._client

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    @property
    def status_text(self) -> str:
        if not self._api_key:
            return "❌ 未配置 API Key（请在界面中填写并保存）"
        masked = self._api_key[:8] + "..." + self._api_key[-4:]
        return f"✅ Kimi 文件内容提取  |  Key: {masked}"

    def ocr(self, image_path: str) -> Optional[dict]:
        """Upload image to Kimi file-extract API.

        Returns dict: {success, full_text, blocks[{text}]} or None.
        """
        if not self._api_key:
            return None
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            client = self._get_client()
            file_object = client.files.create(
                file=path, purpose="file-extract"
            )
            raw_text = client.files.content(file_id=file_object.id).text

            # API returns JSON: {"content":"...", "file_type":"...", ...}
            try:
                data = json.loads(raw_text)
                full_text = data.get("content", raw_text)
            except (json.JSONDecodeError, TypeError):
                full_text = raw_text

            lines = [line for line in full_text.split("\n") if line.strip()]
            blocks = [{"text": line} for line in lines]
            return {
                "success": True,
                "full_text": full_text,
                "blocks": blocks,
            }
        except Exception as e:
            print(f"[OCR] Kimi file-extract error: {e}")
            return None

    def ocr_text(self, image_path: str) -> Optional[str]:
        result = self.ocr(image_path)
        return result.get("full_text") if result else None


# singleton
ocr_engine = OCREngine()
