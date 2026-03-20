from __future__ import annotations

import threading
import time
from typing import Callable, Optional

import mss
import mss.tools
import win32gui
from pynput import mouse

from core.session import Session
from core.window_selector import get_window_rect, bring_window_to_front
from core.ocr_engine import ocr_engine
from models.events import ClickEvent


class Recorder:
    """Records mouse click events on a target window."""

    def __init__(self, session: Session,
                 on_event: Optional[Callable[[ClickEvent], None]] = None,
                 on_auto_stop: Optional[Callable[[], None]] = None,
                 self_hwnd: Optional[int] = None):
        self.session = session
        self.on_event = on_event  # UI callback
        self.on_auto_stop = on_auto_stop  # called when tool window gains focus
        self._self_hwnd = self_hwnd  # HWND of our own tool window
        self._listener: Optional[mouse.Listener] = None
        self._running = False
        self._fg_thread: Optional[threading.Thread] = None

    # ── public API ────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        # bring target window to foreground
        bring_window_to_front(self.session.meta.window_hwnd)
        time.sleep(0.3)

        # start mouse listener
        self._listener = mouse.Listener(
            on_click=self._on_click,
        )
        self._listener.start()

        # start foreground monitor
        if self._self_hwnd:
            self._fg_thread = threading.Thread(
                target=self._monitor_foreground, daemon=True
            )
            self._fg_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        self.session.save()

    @property
    def is_running(self) -> bool:
        return self._running

    # ── foreground monitoring ─────────────────────────────────

    def _monitor_foreground(self) -> None:
        """Periodically check if our tool window came to foreground."""
        while self._running:
            time.sleep(0.3)
            try:
                fg = win32gui.GetForegroundWindow()
                if fg == self._self_hwnd:
                    self._running = False
                    if self._listener:
                        self._listener.stop()
                        self._listener = None
                    self.session.save()
                    if self.on_auto_stop:
                        self.on_auto_stop()
                    return
            except Exception:
                pass

    # ── mouse event handling ──────────────────────────────────

    def _on_click(self, x: int, y: int, button: mouse.Button,
                  pressed: bool) -> None:
        if not self._running:
            return

        hwnd = self.session.meta.window_hwnd
        try:
            rect = get_window_rect(hwnd)
        except Exception:
            return

        # only record clicks inside the target window
        left, top, right, bottom = rect
        if not (left <= x <= right and top <= y <= bottom):
            return

        rel_x = x - left
        rel_y = y - top
        btn_name = button.name if hasattr(button, "name") else str(button)

        event = ClickEvent(
            abs_x=x,
            abs_y=y,
            rel_x=rel_x,
            rel_y=rel_y,
            button=btn_name,
            click_type="press" if pressed else "release",
            timestamp=time.time(),
        )

        # capture screenshot + OCR in background
        threading.Thread(
            target=self._capture_and_ocr,
            args=(event,),
            daemon=True,
        ).start()

    def _capture_and_ocr(self, event: ClickEvent) -> None:
        filepath = None
        try:
            hwnd = self.session.meta.window_hwnd
            rect = get_window_rect(hwnd)
            monitor = {
                "left": rect[0],
                "top": rect[1],
                "width": rect[2] - rect[0],
                "height": rect[3] - rect[1],
            }
            with mss.mss() as sct:
                sct_img = sct.grab(monitor)
            idx = len(self.session.meta.events)
            filename = f"click_{idx:04d}.png"
            filepath = self.session.screenshots_dir / filename
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))
            event.screenshot_path = f"screenshots/{filename}"
        except Exception as e:
            print(f"[Recorder] screenshot error: {e}")

        # run OCR on the captured screenshot
        if filepath and filepath.exists():
            try:
                result = ocr_engine.ocr(str(filepath))
                if result:
                    event.ocr_text = result.get("full_text")
                    event.ocr_result = result.get("blocks")
            except Exception as e:
                print(f"[Recorder] OCR error: {e}")

        self.session.add_event(event)
        if self.on_event:
            self.on_event(event)
