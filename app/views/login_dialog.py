"""Login dialog — shown before the main window on startup."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.models.user import User
from app.services.auth_service import verify_password


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LojaFlow — Login")
        self.setFixedSize(480, 520)
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowType.WindowContextHelpButtonHint
        )
        # Override dialog bg to slate (QSS sets QDialog to white, we want slate here)
        self.setStyleSheet("QDialog { background-color: #f1f5f9; }")
        self.authenticated_user: User | None = None
        self._build_ui()

    def _build_ui(self):
        # Outer layout — centers the card
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # White card
        card = QFrame()
        card.setObjectName("card")
        card.setFixedSize(400, 460)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 32)
        card_layout.setSpacing(0)

        # ── Brand mark ──────────────────────────────────
        brand_row = QHBoxLayout()
        brand_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Indigo square logo badge
        logo_mark = QLabel("LF")
        logo_mark.setFixedSize(48, 48)
        logo_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_mark.setStyleSheet(
            "background-color: #6366f1;"
            "color: #ffffff;"
            "font-size: 18px;"
            "font-weight: bold;"
            "border-radius: 12px;"
        )
        brand_row.addWidget(logo_mark)
        card_layout.addLayout(brand_row)

        card_layout.addSpacing(14)

        app_name = QLabel("LojaFlow")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        app_name.setStyleSheet(
            "font-size: 22px; font-weight: bold; color: #0f172a;"
        )
        card_layout.addWidget(app_name)

        subtitle = QLabel("Sistema de Gestão")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 13px; color: #64748b;")
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(28)

        # ── Form fields ──────────────────────────────────
        user_label = QLabel("Usuário")
        user_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 4px;")
        card_layout.addWidget(user_label)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Digite seu usuário")
        self.username_edit.setFixedHeight(42)
        card_layout.addWidget(self.username_edit)

        card_layout.addSpacing(14)

        pass_label = QLabel("Senha")
        pass_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569; margin-bottom: 4px;")
        card_layout.addWidget(pass_label)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Digite sua senha")
        self.password_edit.setFixedHeight(42)
        self.password_edit.returnPressed.connect(self._do_login)
        card_layout.addWidget(self.password_edit)

        card_layout.addSpacing(20)

        # ── Login button ─────────────────────────────────
        login_btn = QPushButton("Entrar")
        login_btn.setObjectName("btn_primary")
        login_btn.setFixedHeight(46)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(login_btn)

        # ── Error label ──────────────────────────────────
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet(
            "color: #ef4444; font-size: 12px; padding-top: 8px;"
        )
        self.error_label.setWordWrap(True)
        card_layout.addWidget(self.error_label)

        card_layout.addStretch()

        # ── Footer hint ──────────────────────────────────
        hint = QLabel("Padrão: admin / admin123")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("font-size: 11px; color: #94a3b8;")
        card_layout.addWidget(hint)

        outer.addWidget(card)

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
