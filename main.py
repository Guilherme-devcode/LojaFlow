"""LojaFlow — entry point."""
import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app.utils.logger import setup_logging, get_logger
from app.database import init_db
from app.session import Session
from app.views.login_dialog import LoginDialog
from app.views.main_window import MainWindow

_logger = setup_logging()


def _global_exception_hook(exc_type, exc_value, exc_tb):
    """Log unhandled exceptions and show a friendly dialog."""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _logger.critical("Unhandled exception:\n%s", msg)
    try:
        QMessageBox.critical(
            None, "Erro inesperado",
            f"Ocorreu um erro inesperado. Detalhes foram salvos no log.\n\n{exc_value}"
        )
    except Exception:
        pass


def load_stylesheet(app: QApplication) -> None:
    qss_path = Path(__file__).parent / "assets" / "style.qss"
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))


def main() -> int:
    sys.excepthook = _global_exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("LojaFlow")
    app.setApplicationVersion("1.1.0")
    app.setOrganizationName("LojaFlow")

    # Initialize database
    init_db()

    # Apply stylesheet
    load_stylesheet(app)

    # Require login before showing the main window
    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    Session.login(login.authenticated_user)

    # Launch main window
    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
