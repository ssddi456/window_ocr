from __future__ import annotations

import json
import os
import time
from pathlib import Path

from models.events import ClickEvent, SessionMeta

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


class Session:
    """Manages a recording session: creation, saving, and loading."""

    def __init__(self, meta: SessionMeta, base_dir: Path | None = None):
        self.meta = meta
        self.base_dir = base_dir or SESSIONS_DIR
        self.session_dir = self.base_dir / self.meta.session_id
        self.screenshots_dir = self.session_dir / "screenshots"

    # ── creation ──────────────────────────────────────────────

    @classmethod
    def create(cls, window_title: str, window_hwnd: int,
               window_rect: tuple[int, int, int, int]) -> Session:
        session_id = time.strftime("%Y%m%d_%H%M%S")
        meta = SessionMeta(
            session_id=session_id,
            window_title=window_title,
            window_hwnd=window_hwnd,
            window_rect=window_rect,
        )
        session = cls(meta)
        session.screenshots_dir.mkdir(parents=True, exist_ok=True)
        return session

    # ── persistence ───────────────────────────────────────────

    def add_event(self, event: ClickEvent) -> None:
        self.meta.events.append(event)

    def save(self) -> Path:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        path = self.session_dir / "session.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.meta.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, session_dir: str | Path) -> Session:
        session_dir = Path(session_dir)
        path = session_dir / "session.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = SessionMeta.from_dict(data)
        return cls(meta, base_dir=session_dir.parent)

    # ── listing ───────────────────────────────────────────────

    @classmethod
    def list_sessions(cls) -> list[Path]:
        if not SESSIONS_DIR.exists():
            return []
        return sorted(
            [d for d in SESSIONS_DIR.iterdir()
             if d.is_dir() and (d / "session.json").exists()],
            reverse=True,
        )
