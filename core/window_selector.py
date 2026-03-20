from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import win32gui
import win32con


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    rect: tuple[int, int, int, int]  # left, top, right, bottom

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    def __str__(self) -> str:
        return f"{self.title}  [{self.width}x{self.height}]"


def enumerate_windows() -> list[WindowInfo]:
    """Return all visible, titled top-level windows."""
    results: list[WindowInfo] = []

    def _cb(hwnd: int, _: object) -> bool:
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return True
        # skip minimised windows with zero-size rect
        rect = win32gui.GetWindowRect(hwnd)
        if rect[2] - rect[0] <= 0 or rect[3] - rect[1] <= 0:
            return True
        results.append(WindowInfo(hwnd=hwnd, title=title, rect=rect))
        return True

    win32gui.EnumWindows(_cb, None)
    return results


def get_window_rect(hwnd: int) -> tuple[int, int, int, int]:
    """Get current rect for an hwnd (may have moved/resized)."""
    return win32gui.GetWindowRect(hwnd)


def bring_window_to_front(hwnd: int) -> None:
    """Attempt to bring the target window to front."""
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass
