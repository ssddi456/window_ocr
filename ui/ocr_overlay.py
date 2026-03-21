"""Transparent overlay that shows OCR text on top of a target window."""
from __future__ import annotations

from typing import Optional

import win32gui
import win32con

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea


class OCROverlay(QWidget):
    """A frameless, fully transparent, click-through overlay window.

    It tracks the target window position/size and displays OCR text on top of it.
    """

    def __init__(self, hwnd: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._hwnd = hwnd
        self._native_click_through_applied = False
        self._capturing = False  # True while OCR screenshot is in progress

        # frameless, always-on-top, tool window (no taskbar entry)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # translucent background + click-through
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self._build_ui()

        # timer to track target window position
        self._track_timer = QTimer(self)
        self._track_timer.timeout.connect(self._sync_position)
        self._track_timer.start(150)

        self._sync_position()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_native_click_through()

    def _apply_native_click_through(self) -> None:
        """Make overlay truly click-through at native Win32 level."""
        if self._native_click_through_applied:
            return
        try:
            overlay_hwnd = int(self.winId())
            ex_style = win32gui.GetWindowLong(overlay_hwnd, win32con.GWL_EXSTYLE)
            ex_style |= (
                win32con.WS_EX_LAYERED
                | win32con.WS_EX_TRANSPARENT
                | win32con.WS_EX_NOACTIVATE
                | win32con.WS_EX_TOOLWINDOW
            )
            win32gui.SetWindowLong(overlay_hwnd, win32con.GWL_EXSTYLE, ex_style)
            win32gui.SetWindowPos(
                overlay_hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_FRAMECHANGED,
            )
            self._native_click_through_applied = True
        except Exception:
            pass

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(0)
        root_layout.addStretch(3)

        self._panel = QWidget(self)
        self._panel.setStyleSheet("background: transparent;")
        panel_layout = QVBoxLayout(self._panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(8)

        # header label
        self._header = QLabel("🔍 OCR 模式 — 等待识别结果...")
        self._header.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self._header.setStyleSheet(
            "color: #ffffff; background: transparent; padding: 0;"
        )
        self._header.setAlignment(Qt.AlignmentFlag.AlignRight)
        panel_layout.addWidget(self._header)

        # scrollable text area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
            "QScrollBar:vertical { width: 8px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,100); border-radius: 4px; }"
        )
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.viewport().setStyleSheet("background: transparent;")

        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Microsoft YaHei", 10))
        self._text_label.setStyleSheet(
            "color: #ffff00; background: transparent; padding: 0;"
        )
        self._text_label.setWordWrap(True)
        self._text_label.setTextFormat(Qt.TextFormat.PlainText)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
        )
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        scroll.setWidget(self._text_label)
        panel_layout.addWidget(scroll, 1)
        root_layout.addWidget(self._panel, 1)

    def set_text(self, text: str) -> None:
        """Update the displayed OCR text."""
        self._header.setText("🔍 OCR 模式 — 识别结果")
        self._text_label.setText(text.strip())

    def set_waiting(self) -> None:
        self._header.setText("🔍 OCR 模式 — 正在识别...")
        self._text_label.clear()

    def begin_capture(self) -> None:
        """Call before taking an OCR screenshot; hides overlay so it won't appear in the capture."""
        self._capturing = True
        self.hide()

    def end_capture(self) -> None:
        """Call after the OCR screenshot is taken; restores overlay visibility."""
        self._capturing = False
        # _sync_position will decide whether to show on next tick

    def _sync_position(self) -> None:
        """Move/resize to match the target window."""
        try:
            if not win32gui.IsWindow(self._hwnd):
                self.close()
                return

            foreground_hwnd = win32gui.GetForegroundWindow()
            if foreground_hwnd != self._hwnd:
                self.hide()
                return

            if win32gui.IsIconic(self._hwnd):
                self.hide()
                return

            rect = win32gui.GetWindowRect(self._hwnd)
            x, y, r, b = rect
            w = r - x
            h = b - y
            if w > 0 and h > 0:
                if not self._capturing and not self.isVisible():
                    self.show()
                self.setGeometry(x, y, w, h)
            else:
                self.hide()
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self._track_timer.stop()
        super().closeEvent(event)
