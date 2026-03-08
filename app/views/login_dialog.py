"""Login dialog — shown before the main window on startup."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QFormLayout,
)

from app.models.user import User
from app.services.auth_service import verify_password


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LojaFlow — Login")
        self.setMinimumWidth(340)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self.authenticated_user: User | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 32, 32, 24)

        title = QLabel("LojaFlow")
        title.setObjectName("logo_label")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Sistema de gestão para comércio")
        subtitle.setObjectName("stat_label")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        form = QFormLayout()
        form.setSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("admin")
        form.addRow("Usuário:", self.username_edit)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("senha")
        self.password_edit.returnPressed.connect(self._do_login)
        form.addRow("Senha:", self.password_edit)

        layout.addLayout(form)

        login_btn = QPushButton("Entrar")
        login_btn.setObjectName("btn_primary")
        login_btn.setMinimumHeight(42)
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #f38ba8;")
        layout.addWidget(self.error_label)

        layout.addSpacing(4)
        hint = QLabel("Padrão: admin / admin123")
        hint.setObjectName("stat_label")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

    def _do_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self.error_label.setText("Preencha usuário e senha.")
            return

        user = verify_password(username, password)
        if user:
            self.authenticated_user = user
            self.accept()
        else:
            self.error_label.setText("Usuário ou senha incorretos.")
            self.password_edit.clear()
            self.password_edit.setFocus()
