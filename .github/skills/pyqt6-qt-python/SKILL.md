---
name: pyqt6-qt-python
description: 
  "Practical guidelines and recipes for PyQt6 (Qt 6 for Python) in a desktop application. Covers widgets, layouts, signals & slots (pyqtSignal/pyqtSlot), QThread for background processing, QMediaPlayer for video playback, file dialogs, and scoped enums. Triggers when writing or reviewing code that imports from PyQt6, creates QWidget/QMainWindow subclasses, uses Qt signals/slots, or runs background tasks with QThread."
license: MIT
metadata:
  author: project-skill
  version: "1.0.0"
---

# PyQt6 (Qt 6 for Python) Skill

Python bindings for Qt 6 maintained by Riverbank Computing.

- **Package:** `PyQt6` (`pip install PyQt6`)
- **API Reference:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **PyPI:** https://pypi.org/project/PyQt6/
- **Porting from PyQt5:** https://www.riverbankcomputing.com/static/Docs/PyQt6/pyqt5_differences.html

### Key Differences from PySide6

| PySide6 | PyQt6 |
|---|---|
| `from PySide6.QtCore import Signal` | `from PyQt6.QtCore import pyqtSignal` |
| `from PySide6.QtCore import Slot` | `from PyQt6.QtCore import pyqtSlot` |
| `Qt.Horizontal` | `Qt.Orientation.Horizontal` (scoped enums required) |
| `QMessageBox.Yes` | `QMessageBox.StandardButton.Yes` |
| `QKeySequence.Open` | `QKeySequence.StandardKey.Open` |
| `pip install pyside6` | `pip install PyQt6` |
| `--collect-all PySide6` | `--collect-all PyQt6` |

---

## When to Apply

Use this skill when:
- Creating or modifying Qt widgets, windows, or dialogs
- Connecting signals to slots or defining custom signals
- Running heavy work off the main thread (QThread)
- Implementing video playback with `QMediaPlayer`
- Designing layouts (grid, vertical, horizontal, splitters)
- Opening/saving files via `QFileDialog`

---

## Core Application Skeleton

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My App")
        self.resize(1280, 720)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
```

- **One `QApplication` per process** — create before any widgets.
- `app.exec()` starts the event loop; `sys.exit()` forwards the exit code.

---

## Widgets

### Common Widgets

| Widget | Module | Purpose |
|---|---|---|
| `QMainWindow` | `QtWidgets` | Top-level window with menu/toolbar/statusbar |
| `QWidget` | `QtWidgets` | Base class for all UI elements |
| `QPushButton` | `QtWidgets` | Clickable button |
| `QLabel` | `QtWidgets` | Static text or image |
| `QLineEdit` | `QtWidgets` | Single-line text input |
| `QSlider` | `QtWidgets` | Slider (e.g. timeline scrubber) |
| `QProgressBar` | `QtWidgets` | Progress indicator |
| `QComboBox` | `QtWidgets` | Dropdown selector |
| `QListWidget` | `QtWidgets` | Scrollable list of items |
| `QSplitter` | `QtWidgets` | Resizable split panes |
| `QScrollArea` | `QtWidgets` | Scrollable container |
| `QVideoWidget` | `QtMultimediaWidgets` | Video output surface |
| `QGraphicsView` | `QtWidgets` | Custom scene rendering (timeline canvas) |

### Setting Up a Central Widget

```python
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        # add child widgets to layout
```

---

## Layouts

### Layout Types

| Layout | Description |
|---|---|
| `QVBoxLayout` | Stack widgets vertically |
| `QHBoxLayout` | Stack widgets horizontally |
| `QGridLayout` | Place widgets in a grid by row/col |
| `QFormLayout` | Label + field pairs |
| `QStackedLayout` | Show one widget at a time (like tabs) |

```python
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QPushButton, QLabel
)
from PyQt6.QtCore import Qt

# Horizontal split: timeline left, properties right
splitter = QSplitter(Qt.Orientation.Horizontal)
splitter.addWidget(timeline_widget)
splitter.addWidget(properties_widget)
splitter.setStretchFactor(0, 3)   # timeline gets 3x space
splitter.setStretchFactor(1, 1)

# Nested layouts
toolbar = QHBoxLayout()
toolbar.addWidget(QPushButton("Play"))
toolbar.addWidget(QPushButton("Pause"))
toolbar.addStretch()              # push remaining buttons to right

main_layout = QVBoxLayout()
main_layout.addLayout(toolbar)
main_layout.addWidget(splitter)
```

---

## Signals & Slots

Signals decouple UI events from logic. Connect them with `.connect()`.

### Built-in Signal Examples

```python
btn = QPushButton("Export")
btn.clicked.connect(self.on_export)          # no args

slider = QSlider(Qt.Orientation.Horizontal)
slider.valueChanged.connect(self.on_seek)    # int arg

combo = QComboBox()
combo.currentTextChanged.connect(self.on_format_changed)  # str arg
```

### Custom Signals

```python
from PyQt6.QtCore import QObject, pyqtSignal

class VideoProcessor(QObject):
    progress_changed = pyqtSignal(int)    # emits an int (0-100)
    finished         = pyqtSignal(str)    # emits output file path
    error_occurred   = pyqtSignal(str)    # emits error message

    def process(self):
        # ... do work ...
        self.progress_changed.emit(50)
        self.finished.emit('output.mp4')
```

### Connecting Signals to Slots

```python
processor = VideoProcessor()
processor.progress_changed.connect(progress_bar.setValue)   # direct binding
processor.finished.connect(lambda path: self.show_done(path))
processor.error_occurred.connect(self.show_error)

# Disconnect when done
processor.progress_changed.disconnect(progress_bar.setValue)
```

---

## Background Threads (QThread)

**Never run ffmpeg or other blocking code on the main thread** — it freezes the UI.

### Pattern: Worker + QThread

```python
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import ffmpeg

class FfmpegWorker(QObject):
    progress = pyqtSignal(int)        # 0-100
    finished = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str):
        super().__init__()
        self._input  = input_path
        self._output = output_path

    def run(self):
        try:
            import re, subprocess
            process = (
                ffmpeg
                .input(self._input)
                .output(self._output, vcodec='libx264')
                .overwrite_output()
                .run_async(pipe_stderr=True)
            )
            # Parse ffmpeg stderr to emit progress
            duration = self._get_duration()
            for line in process.stderr:
                m = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line.decode('utf-8', errors='ignore'))
                if m and duration:
                    elapsed = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
                    self.progress.emit(int(elapsed / duration * 100))
            process.wait()
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _get_duration(self) -> float:
        info = ffmpeg.probe(self._input)
        return float(info['format'].get('duration', 0))


class ExportController:
    def start_export(self, input_path, output_path):
        self.thread = QThread()
        self.worker = FfmpegWorker(input_path, output_path)
        self.worker.moveToThread(self.thread)

        # Wire up signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.error.connect(self.show_error)

        self.thread.start()
```

> **Key rules:**
> - Call `worker.moveToThread(thread)` before starting.
> - Connect `thread.started` to the worker's `run` slot.
> - Always clean up with `deleteLater` to avoid memory leaks.
> - Do NOT access Qt widgets from the worker thread — use signals only.

---

## Video Playback (QMediaPlayer)

```python
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl

class VideoPlayer(QWidget):
    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio  = QAudioOutput()
        self.player.setAudioOutput(self.audio)

        self.video_widget = QVideoWidget()
        self.player.setVideoOutput(self.video_widget)

        layout = QVBoxLayout(self)
        layout.addWidget(self.video_widget)

        # Controls
        controls = QHBoxLayout()
        self.play_btn  = QPushButton("Play")
        self.pause_btn = QPushButton("Pause")
        self.slider    = QSlider(Qt.Orientation.Horizontal)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.slider)
        layout.addLayout(controls)

        # Connect
        self.play_btn.clicked.connect(self.player.play)
        self.pause_btn.clicked.connect(self.player.pause)
        self.player.positionChanged.connect(self.on_position_changed)
        self.player.durationChanged.connect(self.on_duration_changed)
        self.slider.sliderMoved.connect(self.player.setPosition)

    def load(self, path: str):
        self.player.setSource(QUrl.fromLocalFile(path))

    def on_position_changed(self, pos_ms: int):
        self.slider.setValue(pos_ms)

    def on_duration_changed(self, duration_ms: int):
        self.slider.setRange(0, duration_ms)
```

### Key QMediaPlayer Signals

| Signal | Args | Description |
|---|---|---|
| `positionChanged` | `int` (ms) | Current playback position |
| `durationChanged` | `int` (ms) | Total media duration |
| `playbackStateChanged` | `QMediaPlayer.PlaybackState` | Playing / Paused / Stopped |
| `errorOccurred` | `error`, `errorString` | Playback error |
| `mediaStatusChanged` | `QMediaPlayer.MediaStatus` | Loaded / Buffering / EndOfMedia |

---

## File Dialogs

```python
from PyQt6.QtWidgets import QFileDialog

# Open a video file
path, _ = QFileDialog.getOpenFileName(
    self,
    "Open Video",
    "",                                              # initial dir
    "Video Files (*.mp4 *.avi *.mkv *.mov);;All Files (*)"
)
if path:
    self.load_video(path)

# Save output file
out_path, _ = QFileDialog.getSaveFileName(
    self,
    "Save As",
    "output.mp4",
    "MP4 Video (*.mp4);;All Files (*)"
)

# Open a directory
folder = QFileDialog.getExistingDirectory(self, "Select Folder")
```

---

## Menu Bar & Toolbar

```python
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QMenuBar, QToolBar

class MainWindow(QMainWindow):
    def _setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        open_action = QAction("&Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)  # Ctrl+O
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        export_action = QAction("&Export…", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.export)
        file_menu.addAction(export_action)

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction("Play",  self.play)
        toolbar.addAction("Pause", self.pause)
        toolbar.addAction("Export", self.export)
```

---

## Status Bar & Progress

```python
# In QMainWindow
self.statusBar().showMessage("Ready")
self.statusBar().showMessage("Exporting…", 3000)   # 3s timeout

# Persistent widget in status bar
self.progress = QProgressBar()
self.progress.setRange(0, 100)
self.statusBar().addPermanentWidget(self.progress)
```

---

## Common Patterns for a Video Editor

### Disable UI during export

```python
def start_export(self):
    self.export_btn.setEnabled(False)
    self.open_btn.setEnabled(False)
    # ... start QThread worker ...

def on_export_finished(self):
    self.export_btn.setEnabled(True)
    self.open_btn.setEnabled(True)
    self.statusBar().showMessage("Export complete!")
```

### Show error dialog

```python
from PyQt6.QtWidgets import QMessageBox

def show_error(self, message: str):
    QMessageBox.critical(self, "Error", message)
```

### Confirm before closing

```python
def closeEvent(self, event):
    reply = QMessageBox.question(
        self, "Quit", "Are you sure you want to quit?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    if reply == QMessageBox.StandardButton.Yes:
        event.accept()
    else:
        event.ignore()
```

---

## Common Pitfalls

| Issue | Solution |
|---|---|
| UI freezes during ffmpeg | Move ffmpeg to a `QThread` worker |
| Crash when accessing widget from thread | Only update widgets via signals |
| `QMediaPlayer` shows no video | Must set `QVideoWidget` as output _before_ loading media |
| Worker runs on main thread | Call `moveToThread()` before connecting `started` |
| Memory leak with QThread | Connect `finished` to `deleteLater` on both worker and thread |
| `QApplication` must exist first | Instantiate `QApplication` before any `QWidget` |
| PyInstaller missing Qt plugins | Add `--collect-all PyQt6` to PyInstaller args |

---

## Module Import Reference

```python
# Widgets
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QPushButton, QLabel, QLineEdit, QSlider, QProgressBar,
    QComboBox, QListWidget, QSplitter, QScrollArea,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QFileDialog, QMessageBox, QToolBar,
)
# Core (signals, threads, timers, URLs)
from PyQt6.QtCore import (
    Qt, QObject, QThread, pyqtSignal, pyqtSlot,
    QTimer, QUrl, QSize,
)
# GUI (actions, icons, key sequences)
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QPixmap

# Multimedia
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
```

---

## References

- **API Reference:** https://www.riverbankcomputing.com/static/Docs/PyQt6/
- **PyPI:** https://pypi.org/project/PyQt6/
- **Differences from PyQt5:** https://www.riverbankcomputing.com/static/Docs/PyQt6/pyqt5_differences.html
- **QMediaPlayer:** https://www.riverbankcomputing.com/static/Docs/PyQt6/api/qtmultimedia/qmediaplayer.html
- **QThread:** https://www.riverbankcomputing.com/static/Docs/PyQt6/api/qtcore/qthread.html
- **QFileDialog:** https://www.riverbankcomputing.com/static/Docs/PyQt6/api/qtwidgets/qfiledialog.html
- **Signals & Slots:** https://www.riverbankcomputing.com/static/Docs/PyQt6/signals_slots.html
- **Scoped Enums:** https://www.riverbankcomputing.com/static/Docs/PyQt6/pyqt5_differences.html#scoped-enums
