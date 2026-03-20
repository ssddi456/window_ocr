"""Window OCR - 操作录制与回放工具"""

import signal
import sys
from pathlib import Path

# ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # allow Ctrl+C in terminal to close the app
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
