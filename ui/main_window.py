from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QStatusBar, QSplitter,
)

from core.window_selector import WindowInfo, enumerate_windows
from core.session import Session
from core.recorder import Recorder
from core.player import Player
from core.ocr_engine import ocr_engine
from models.events import ClickEvent


class _Signals(QObject):
    """Thread-safe signals for callbacks from recorder/player threads."""
    event_recorded = pyqtSignal(object)  # ClickEvent
    playback_event = pyqtSignal(int, object)  # index, ClickEvent
    playback_done = pyqtSignal()
    recording_auto_stopped = pyqtSignal()  # when tool window gains focus


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Window OCR - 操作录制与回放")
        self.setMinimumSize(600, 500)

        self._signals = _Signals()
        self._signals.event_recorded.connect(self._on_event_recorded)
        self._signals.playback_event.connect(self._on_playback_event)
        self._signals.playback_done.connect(self._on_playback_done)
        self._signals.recording_auto_stopped.connect(self._on_recording_auto_stopped)

        self._windows: list[WindowInfo] = []
        self._selected_window: Optional[WindowInfo] = None
        self._recorder: Optional[Recorder] = None
        self._player: Optional[Player] = None

        self._build_ui()
        self._update_state()

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # -- window selection --
        win_group = QGroupBox("窗口选择")
        win_layout = QVBoxLayout(win_group)

        row = QHBoxLayout()
        self._combo_windows = QComboBox()
        self._combo_windows.setMinimumWidth(350)
        self._combo_windows.currentIndexChanged.connect(self._on_window_selected)
        row.addWidget(self._combo_windows, 1)

        self._btn_refresh = QPushButton("刷新窗口列表")
        self._btn_refresh.clicked.connect(self._refresh_windows)
        row.addWidget(self._btn_refresh)
        win_layout.addLayout(row)

        self._lbl_window_info = QLabel("请选择目标窗口")
        win_layout.addWidget(self._lbl_window_info)
        layout.addWidget(win_group)

        # -- OCR status --
        ocr_group = QGroupBox("OCR 引擎 (PaddleOCR)")
        ocr_layout = QHBoxLayout(ocr_group)
        self._lbl_ocr_status = QLabel("检测中...")
        ocr_layout.addWidget(self._lbl_ocr_status, 1)
        self._btn_ocr_check = QPushButton("检测连接")
        self._btn_ocr_check.clicked.connect(self._detect_ocr_status)
        ocr_layout.addWidget(self._btn_ocr_check)
        layout.addWidget(ocr_group)
        self._detect_ocr_status()

        # -- controls --
        ctrl_group = QGroupBox("控制")
        ctrl_layout = QHBoxLayout(ctrl_group)

        self._btn_record = QPushButton("▶ 开始录制")
        self._btn_record.clicked.connect(self._toggle_record)
        ctrl_layout.addWidget(self._btn_record)

        self._btn_play = QPushButton("▶ 回放")
        self._btn_play.clicked.connect(self._toggle_playback)
        ctrl_layout.addWidget(self._btn_play)

        layout.addWidget(ctrl_group)

        # -- session list --
        session_group = QGroupBox("历史 Session")
        session_layout = QVBoxLayout(session_group)

        self._btn_refresh_sessions = QPushButton("刷新 Session 列表")
        self._btn_refresh_sessions.clicked.connect(self._refresh_sessions)
        session_layout.addWidget(self._btn_refresh_sessions)

        self._list_sessions = QListWidget()
        self._list_sessions.itemClicked.connect(self._on_session_selected)
        session_layout.addWidget(self._list_sessions)

        layout.addWidget(session_group)

        # -- event log --
        log_group = QGroupBox("事件日志")
        log_layout = QVBoxLayout(log_group)
        self._list_events = QListWidget()
        log_layout.addWidget(self._list_events)
        layout.addWidget(log_group)

        # status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("就绪")

        # initial data
        self._refresh_windows()
        self._refresh_sessions()

    # ── OCR status ─────────────────────────────────────────────

    def _detect_ocr_status(self) -> None:
        health = ocr_engine.check_health()
        url = ocr_engine.server_url
        if health.get("status") == "ok":
            engine = health.get("engine", "PaddleOCR")
            self._lbl_ocr_status.setText(
                f"✅ 已连接  {engine}  |  {url}"
            )
            self._lbl_ocr_status.setStyleSheet("color: green;")
        else:
            err = health.get("error", "未知错误")
            self._lbl_ocr_status.setText(
                f"❌ 无法连接 OCR 服务  |  {url}\n"
                f"   请先启动: python ocr_server.py\n"
                f"   错误: {err}"
            )
            self._lbl_ocr_status.setStyleSheet("color: red;")

    # ── window selection ──────────────────────────────────────

    def _refresh_windows(self) -> None:
        self._combo_windows.blockSignals(True)
        self._combo_windows.clear()
        self._windows = enumerate_windows()
        for w in self._windows:
            self._combo_windows.addItem(str(w))
        self._combo_windows.blockSignals(False)
        if self._windows:
            self._combo_windows.setCurrentIndex(0)
            self._on_window_selected(0)

    def _on_window_selected(self, index: int) -> None:
        if 0 <= index < len(self._windows):
            self._selected_window = self._windows[index]
            self._lbl_window_info.setText(
                f"HWND: {self._selected_window.hwnd}  |  "
                f"大小: {self._selected_window.width}x{self._selected_window.height}"
            )
        self._update_state()

    # ── recording ─────────────────────────────────────────────

    def _toggle_record(self) -> None:
        if self._recorder and self._recorder.is_running:
            self._stop_recording()
        else:
            self._start_recording()

    def _get_self_hwnd(self) -> int:
        """Get the HWND of our own Qt window."""
        return int(self.winId())

    def _start_recording(self) -> None:
        if not self._selected_window:
            QMessageBox.warning(self, "提示", "请先选择目标窗口")
            return

        w = self._selected_window
        session = Session.create(w.title, w.hwnd, w.rect)
        self._recorder = Recorder(
            session,
            on_event=lambda e: self._signals.event_recorded.emit(e),
            on_auto_stop=lambda: self._signals.recording_auto_stopped.emit(),
            self_hwnd=self._get_self_hwnd(),
        )
        self._list_events.clear()
        self._recorder.start()
        self._status.showMessage(f"录制中 — {w.title}")
        self._update_state()

    def _stop_recording(self) -> None:
        if self._recorder:
            self._recorder.stop()
            n = len(self._recorder.session.meta.events)
            self._status.showMessage(f"录制完成，共 {n} 个事件")
            self._recorder = None
        self._refresh_sessions()
        self._update_state()

    # ── playback ──────────────────────────────────────────────

    def _toggle_playback(self) -> None:
        if self._player and self._player.is_running:
            self._player.stop()
            self._status.showMessage("回放已停止")
            self._update_state()
            return

        # try to load selected session
        item = self._list_sessions.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先在历史列表中选择一个 Session")
            return
        session_dir = Path(item.data(Qt.ItemDataRole.UserRole))
        session = Session.load(session_dir)

        self._list_events.clear()
        self._player = Player(
            session,
            on_event=lambda i, e: self._signals.playback_event.emit(i, e),
            on_done=lambda: self._signals.playback_done.emit(),
        )
        self._player.start()
        self._status.showMessage(
            f"回放中 — {session.meta.window_title} "
            f"({len(session.meta.events)} 个事件)"
        )
        self._update_state()

    # ── sessions list ─────────────────────────────────────────

    def _refresh_sessions(self) -> None:
        self._list_sessions.clear()
        for d in Session.list_sessions():
            try:
                s = Session.load(d)
                label = (f"{s.meta.session_id}  |  {s.meta.window_title}  |  "
                         f"{len(s.meta.events)} 事件")
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, str(d))
                self._list_sessions.addItem(item)
            except Exception:
                continue

    def _on_session_selected(self, item: QListWidgetItem) -> None:
        self._update_state()

    # ── signal handlers (thread-safe) ─────────────────────────

    def _on_event_recorded(self, event: ClickEvent) -> None:
        idx = len(self._recorder.session.meta.events) if self._recorder else 0
        ocr_info = ""
        if event.ocr_text:
            preview = event.ocr_text[:50].replace("\n", " ")
            ocr_info = f"  OCR: {preview}..."
        self._list_events.addItem(
            f"[{idx}] {event.click_type} {event.button}  "
            f"({event.rel_x}, {event.rel_y}){ocr_info}"
        )
        self._list_events.scrollToBottom()

    def _on_playback_event(self, index: int, event: ClickEvent) -> None:
        self._list_events.addItem(
            f"▶ [{index}] {event.click_type} {event.button}  "
            f"({event.rel_x}, {event.rel_y})"
        )
        self._list_events.scrollToBottom()

    def _on_playback_done(self) -> None:
        self._status.showMessage("回放完成")
        self._player = None
        self._update_state()

    def _on_recording_auto_stopped(self) -> None:
        """Called when recording stops because our window gained focus."""
        if self._recorder:
            n = len(self._recorder.session.meta.events)
            self._status.showMessage(f"录制自动停止（窗口切回），共 {n} 个事件")
            self._recorder = None
        self._refresh_sessions()
        self._update_state()

    # ── button state management ───────────────────────────────

    def _update_state(self) -> None:
        recording = self._recorder is not None and self._recorder.is_running
        playing = self._player is not None and self._player.is_running
        has_window = self._selected_window is not None
        has_session = self._list_sessions.currentItem() is not None

        self._btn_record.setEnabled(has_window and not playing)
        self._btn_record.setText("⏹ 停止录制" if recording else "▶ 开始录制")

        self._btn_play.setEnabled(has_session and not recording)
        self._btn_play.setText("⏹ 停止回放" if playing else "▶ 回放")

        self._combo_windows.setEnabled(not recording and not playing)
        self._btn_refresh.setEnabled(not recording and not playing)
