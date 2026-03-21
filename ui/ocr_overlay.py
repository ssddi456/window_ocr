"""Transparent overlay that shows OCR text on top of a target window."""
from __future__ import annotations

from typing import Optional

import win32gui

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QScrollArea


class OCROverlay(QWidget):
    """A frameless, semi-transparent, click-through overlay window.

    It tracks the target window position/size and displays OCR text on top of it.
    """

    def __init__(self, hwnd: int, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._hwnd = hwnd

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
        self._track_timer.start(200)

        self._sync_position()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # header label
        self._header = QLabel("🔍 OCR 模式 — 等待识别结果...")
        self._header.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self._header.setStyleSheet(
            "color: #ffffff; background: rgba(0,0,0,180); "
            "border-radius: 4px; padding: 4px 8px;"
        )
        self._header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._header)

        # scrollable text area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 8px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,100); border-radius: 4px; }"
        )

        self._text_label = QLabel("")
        self._text_label.setFont(QFont("Microsoft YaHei", 10))
        self._text_label.setStyleSheet(
            "color: #ffff00; background: rgba(0,0,0,140); "
            "border-radius: 4px; padding: 8px;"
        )
        self._text_label.setWordWrap(True)
        self._text_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self._text_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        scroll.setWidget(self._text_label)
        layout.addWidget(scroll, 1)

    def paintEvent(self, event) -> None:
        """Draw semi-transparent background with border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # dark overlay
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        # border
        pen = QPen(QColor(0, 200, 255, 200), 2)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        painter.end()

    def set_text(self, text: str) -> None:
        """Update the displayed OCR text."""
        self._header.setText("🔍 OCR 模式 — 识别结果")
        self._text_label.setText(text)

    def set_waiting(self) -> None:
        self._header.setText("🔍 OCR 模式 — 正在识别...")

    def _sync_position(self) -> None:
        """Move/resize to match the target window."""
        try:
            rect = win32gui.GetWindowRect(self._hwnd)
            x, y, r, b = rect
            w = r - x
            h = b - y
            if w > 0 and h > 0:
                self.setGeometry(x, y, w, h)
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        self._track_timer.stop()
        super().closeEvent(event)
