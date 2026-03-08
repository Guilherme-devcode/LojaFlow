"""User management panel — embedded in the Settings page."""
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.user_service import deactivate_user, list_users, reactivate_user


class UserManagementWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Usuários do Sistema")
        title.setObjectName("stat_label")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("+ Novo Usuário")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add_user)
        header.addWidget(add_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Usuário", "Perfil", "Ações"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 180)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 110)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def _load(self):
        users = list_users()
        self.table.setRowCount(len(users))
        role_labels = {"admin": "Administrador", "cashier": "Caixa"}

        for row, u in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(u.id)))
            name_item = QTableWidgetItem(u.name + ("" if u.active else "  [inativo]"))
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, QTableWidgetItem(u.username))
            self.table.setItem(row, 3, QTableWidgetItem(role_labels.get(u.role, u.role)))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            edit_btn = QPushButton("Editar")
            edit_btn.setFixedHeight(26)
            edit_btn.clicked.connect(lambda _, uid=u.id: self._edit_user(uid))
            al.addWidget(edit_btn)

            if u.active and u.username != "admin":
                deact_btn = QPushButton("Desativar")
                deact_btn.setObjectName("btn_danger")
                deact_btn.setFixedHeight(26)
                deact_btn.clicked.connect(lambda _, uid=u.id: self._deactivate(uid))
                al.addWidget(deact_btn)
            elif not u.active:
                react_btn = QPushButton("Reativar")
                react_btn.setObjectName("btn_success")
                react_btn.setFixedHeight(26)
                react_btn.clicked.connect(lambda _, uid=u.id: self._reactivate(uid))
                al.addWidget(react_btn)

            self.table.setCellWidget(row, 4, actions)
            self.table.setRowHeight(row, 36)

    def _add_user(self):
        from app.views.settings.user_form_dialog import UserFormDialog
        dlg = UserFormDialog(parent=self)
        if dlg.exec():
            self._load()

    def _edit_user(self, user_id: int):
        from app.database import get_session
        from app.models.user import User
        with get_session() as s:
            user = s.get(User, user_id)
        if not user:
            return
        from app.views.settings.user_form_dialog import UserFormDialog
        dlg = UserFormDialog(user=user, parent=self)
        if dlg.exec():
            self._load()

    def _deactivate(self, user_id: int):
        reply = QMessageBox.question(
            self, "Desativar usuário",
            "Desativar este usuário? Ele não poderá mais fazer login.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                deactivate_user(user_id)
                self._load()
            except Exception as exc:
                QMessageBox.critical(self, "Erro", str(exc))

    def _reactivate(self, user_id: int):
        try:
            reactivate_user(user_id)
            self._load()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
