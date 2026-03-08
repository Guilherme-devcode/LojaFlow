"""Dialog to create or edit a user."""
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.models.user import User
from app.services.user_service import create_user, update_user


class UserFormDialog(QDialog):
    def __init__(self, user: User | None = None, parent=None):
        super().__init__(parent)
        self._user = user
        self.setWindowTitle("Novo Usuário" if not user else "Editar Usuário")
        self.setMinimumWidth(360)
        self._build_ui()
        if user:
            self._populate(user)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        form.addRow("Nome completo *", self.name_edit)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("login")
        if self._user:
            self.username_edit.setEnabled(False)
        form.addRow("Usuário *", self.username_edit)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Caixa (cashier)", "cashier")
        self.role_combo.addItem("Administrador (admin)", "admin")
        form.addRow("Perfil", self.role_combo)

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Mínimo 4 caracteres" if not self._user else "Deixe em branco para não alterar")
        form.addRow("Senha" + ("" if self._user else " *"), self.password_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, user: User):
        self.name_edit.setText(user.name)
        self.username_edit.setText(user.username)
        idx = self.role_combo.findData(user.role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

    def _save(self):
        name = self.name_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        role = self.role_combo.currentData()

        if not name:
            QMessageBox.warning(self, "Atenção", "O nome é obrigatório.")
            return

        if not self._user:
            if not username:
                QMessageBox.warning(self, "Atenção", "O usuário é obrigatório.")
                return
            if len(password) < 4:
                QMessageBox.warning(self, "Atenção", "A senha deve ter pelo menos 4 caracteres.")
                return

        try:
            if self._user:
                update_user(self._user.id, name, role, new_password=password or None)
            else:
                create_user(name, username, password, role)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
