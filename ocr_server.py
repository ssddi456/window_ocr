"""PaddleOCR HTTP Server.

Provides an OCR endpoint that accepts image uploads and returns
text + layout information using PaddleOCR.

Usage:
    python ocr_server.py                   # uses config.json
    python ocr_server.py --port 8089       # override port
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

# ── pythonw compatibility: redirect stdio to log file ─────────
LOG_DIR = Path(__file__).resolve().parent
LOG_FILE = LOG_DIR / "ocr_server.log"

if sys.stdout is None or sys.stderr is None:
    _log_fh = open(LOG_FILE, "a", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _log_fh
    if sys.stderr is None:
        sys.stderr = _log_fh

from a2wsgi import ASGIMiddleware
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

# ── load config ───────────────────────────────────────────────

CONFIG_DIR = Path(__file__).resolve().parent
CONFIG_PATH = CONFIG_DIR / "config.json"
CONFIG_LOCAL_PATH = CONFIG_DIR / "config.local.json"


def load_config() -> dict:
    cfg = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    if CONFIG_LOCAL_PATH.exists():
        with open(CONFIG_LOCAL_PATH, "r", encoding="utf-8") as f:
            local = json.load(f)
        for k, v in local.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


config = load_config()
server_cfg = config.get("ocr_server", {})
DEFAULT_HOST = server_cfg.get("host", "127.0.0.1")
DEFAULT_PORT = server_cfg.get("port", 8089)

# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(title="PaddleOCR Server", version="1.0.0")

# lazy-init PaddleOCR instance
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        from paddleocr import PaddleOCR
        _ocr_engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        print("[OCR Server] PaddleOCR engine loaded.")
    return _ocr_engine


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "PaddleOCR"}


@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    """Accept an image upload and return OCR results with text + layout."""
    start = time.time()

    # save uploaded file to a temp location
    suffix = Path(file.filename).suffix if file.filename else ".png"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        engine = get_ocr_engine()
        results = engine.predict(tmp_path)

        blocks = []
        full_lines = []

        for res in results:
            if not hasattr(res, "__iter__"):
                continue
            # PaddleOCR 3.x: result object has 'rec_texts', 'rec_scores',
            # 'dt_polys' attributes
            if hasattr(res, "rec_texts"):
                texts = res.rec_texts if res.rec_texts else []
                scores = res.rec_scores if res.rec_scores else []
                polys = res.dt_polys if res.dt_polys else []

                for i, text in enumerate(texts):
                    block = {
                        "text": text,
                        "confidence": float(scores[i]) if i < len(scores) else 0.0,
                    }
                    if i < len(polys):
                        poly = polys[i]
                        # convert numpy array to list
                        if hasattr(poly, "tolist"):
                            poly = poly.tolist()
                        block["bbox"] = poly
                    blocks.append(block)
                    full_lines.append(text)
            else:
                # fallback: try dict-style access
                try:
                    for item in res:
                        if isinstance(item, dict):
                            block = {
                                "text": item.get("text", ""),
                                "confidence": float(item.get("score", 0)),
                            }
                            if "bbox" in item:
                                block["bbox"] = item["bbox"]
                            elif "poly" in item:
                                block["bbox"] = item["poly"]
                            blocks.append(block)
                            full_lines.append(block["text"])
                except (TypeError, KeyError):
                    pass

        elapsed = time.time() - start
        return JSONResponse({
            "success": True,
            "blocks": blocks,
            "full_text": "\n".join(full_lines),
            "elapsed_ms": round(elapsed * 1000, 1),
        })

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=500,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# ── main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PaddleOCR HTTP Server")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger("ocr_server")

    log.info("Starting on %s:%s", args.host, args.port)
    log.info("POST /ocr  — upload image for OCR")
    log.info("GET  /health — health check")

    # pre-load the engine
    get_ocr_engine()

    from waitress import serve
    wsgi_app = ASGIMiddleware(app)
    serve(wsgi_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
