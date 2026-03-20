from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ClickEvent:
    """Represents a single mouse click event during recording."""

    abs_x: int  # absolute screen x
    abs_y: int  # absolute screen y
    rel_x: int  # relative to target window x
    rel_y: int  # relative to target window y
    button: str  # "left", "right", "middle"
    click_type: str  # "press" or "release"
    timestamp: float = field(default_factory=time.time)
    screenshot_path: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_result: Optional[list] = None  # [{text, confidence, bbox}, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ClickEvent:
        return cls(**data)


@dataclass
class SessionMeta:
    """Metadata for a recording session."""

    session_id: str
    window_title: str
    window_hwnd: int
    window_rect: tuple[int, int, int, int]  # left, top, right, bottom
    created_at: float = field(default_factory=time.time)
    events: list[ClickEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["events"] = [e.to_dict() for e in self.events]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SessionMeta:
        events = [ClickEvent.from_dict(e) for e in data.pop("events", [])]
        data["window_rect"] = tuple(data["window_rect"])
        return cls(**data, events=events)
