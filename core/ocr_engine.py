"""OCR client — sends images to PaddleOCR HTTP server for recognition."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _load_server_url() -> str:
    """Read OCR server address from config.json."""
    host = "127.0.0.1"
    port = 8089
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            srv = cfg.get("ocr_server", {})
            host = srv.get("host", host)
            port = srv.get("port", port)
        except Exception:
            pass
    return f"http://{host}:{port}"


class OCREngine:
    """HTTP client for the PaddleOCR server."""

    def __init__(self) -> None:
        self._server_url = _load_server_url()

    def reload_config(self) -> None:
        self._server_url = _load_server_url()

    @property
    def server_url(self) -> str:
        return self._server_url

    # ── health check ──────────────────────────────────────────

    def check_health(self) -> dict:
        """Ping the OCR server. Returns {"status": "ok", ...} or error info."""
        try:
            url = f"{self._server_url}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as e:
            return {"status": "unreachable", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @property
    def available(self) -> bool:
        return self.check_health().get("status") == "ok"

    # ── OCR request ───────────────────────────────────────────

    def ocr(self, image_path: str) -> Optional[dict]:
        """Send an image to the OCR server.

        Returns dict with keys: full_text, blocks[{text, confidence, bbox}]
        or None on failure.
        """
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            # build multipart/form-data body
            boundary = "----PaddleOCRBoundary"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; '
                f'filename="{path.name}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode()
            body += path.read_bytes()
            body += f"\r\n--{boundary}--\r\n".encode()

            url = f"{self._server_url}/ocr"
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())

            if result.get("success"):
                return result
            else:
                print(f"[OCR] Server error: {result.get('error')}")
                return None

        except Exception as e:
            print(f"[OCR] Request failed: {e}")
            return None

    def ocr_text(self, image_path: str) -> Optional[str]:
        """Convenience: return just the full_text string."""
        result = self.ocr(image_path)
        if result:
            return result.get("full_text")
        return None


# singleton instance
ocr_engine = OCREngine()
