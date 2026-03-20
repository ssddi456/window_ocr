from __future__ import annotations

import time
import threading
from typing import Callable, Optional

import pyautogui

from core.session import Session
from core.window_selector import bring_window_to_front, get_window_rect
from models.events import ClickEvent

# safety: disable pyautogui's fail-safe pause
pyautogui.PAUSE = 0.05


class Player:
    """Replays recorded mouse events on the target window."""

    def __init__(self, session: Session,
                 on_event: Optional[Callable[[int, ClickEvent], None]] = None,
                 on_done: Optional[Callable[[], None]] = None):
        self.session = session
        self.on_event = on_event  # (index, event) callback
        self.on_done = on_done
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ── public API ────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # ── internal ──────────────────────────────────────────────

    def _run(self) -> None:
        events = self.session.meta.events
        if not events:
            self._running = False
            if self.on_done:
                self.on_done()
            return

        hwnd = self.session.meta.window_hwnd
        bring_window_to_front(hwnd)
        time.sleep(0.3)

        try:
            current_rect = get_window_rect(hwnd)
        except Exception:
            current_rect = self.session.meta.window_rect

        orig_rect = self.session.meta.window_rect
        # compute offset if window has moved
        offset_x = current_rect[0] - orig_rect[0]
        offset_y = current_rect[1] - orig_rect[1]

        prev_ts = events[0].timestamp

        for i, event in enumerate(events):
            if not self._running:
                break

            # wait for the time delta between events
            delta = event.timestamp - prev_ts
            if delta > 0:
                time.sleep(min(delta, 5.0))  # cap max wait at 5s
            prev_ts = event.timestamp

            # only replay press events to avoid double-clicks
            if event.click_type != "press":
                if self.on_event:
                    self.on_event(i, event)
                continue

            target_x = event.abs_x + offset_x
            target_y = event.abs_y + offset_y

            btn = event.button
            if btn == "left":
                pyautogui.click(target_x, target_y, button="left")
            elif btn == "right":
                pyautogui.click(target_x, target_y, button="right")
            elif btn == "middle":
                pyautogui.click(target_x, target_y, button="middle")

            if self.on_event:
                self.on_event(i, event)

        self._running = False
        if self.on_done:
            self.on_done()
