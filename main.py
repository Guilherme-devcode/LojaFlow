"""LojaFlow — entry point."""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.database import init_db
from app.views.main_window import MainWindow


def load_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LojaFlow")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LojaFlow")

    # Initialize database
    init_db()

    # Apply stylesheet
    load_stylesheet(app)

    # Launch main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
