"""OCR Monitor — periodically screenshots a target window and runs OCR."""
from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import mss
import mss.tools

from core.ocr_engine import ocr_engine
from core.window_selector import get_window_rect


class OCRMonitor:
    """Takes a screenshot of the target window every *interval* seconds,
    runs OCR, and fires *on_result* with the extracted text."""

    def __init__(
        self,
        hwnd: int,
        interval: float = 3.0,
        on_result: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        before_capture: Optional[Callable[[], None]] = None,
        after_capture: Optional[Callable[[], None]] = None,
    ):
        self._hwnd = hwnd
        self._interval = interval
        self.on_result = on_result
        self.on_error = on_error
        self.before_capture = before_capture
        self.after_capture = after_capture
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tmp_dir = tempfile.mkdtemp(prefix="ocr_monitor_")

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        # clean up temp files
        try:
            import shutil
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
        except Exception:
            pass

    def _loop(self) -> None:
        counter = 0
        while self._running:
            try:
                self._tick(counter)
            except Exception as e:
                if self.on_error:
                    self.on_error(str(e))
            counter += 1
            # sleep in small increments so stop() is responsive
            deadline = time.monotonic() + self._interval
            while self._running and time.monotonic() < deadline:
                time.sleep(0.2)

    def _tick(self, counter: int) -> None:
        rect = get_window_rect(self._hwnd)
        monitor = {
            "left": rect[0],
            "top": rect[1],
            "width": rect[2] - rect[0],
            "height": rect[3] - rect[1],
        }
        if monitor["width"] <= 0 or monitor["height"] <= 0:
            return

        # capture
        if self.before_capture:
            self.before_capture()
            time.sleep(0.08)

        try:
            with mss.mss() as sct:
                sct_img = sct.grab(monitor)
        finally:
            if self.after_capture:
                self.after_capture()

        filepath = Path(self._tmp_dir) / f"ocr_{counter:06d}.png"
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))

        # OCR
        result = ocr_engine.ocr(str(filepath))

        # remove temp file immediately
        try:
            filepath.unlink()
            pass
        except Exception:
            pass

        if not self.on_result:
            return

        full_text = ""
        if result:
            full_text = str(result.get("full_text") or "")

        self.on_result(full_text)
