"""Customer registry view."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database import get_session
from app.models.customer import Customer


def list_customers(search: str = "") -> list[Customer]:
    with get_session() as s:
        q = s.query(Customer)
        if search:
            like = f"%{search}%"
            q = q.filter(Customer.name.ilike(like) | Customer.phone.ilike(like))
        return q.order_by(Customer.name).all()


def save_customer(customer_id: int | None, data: dict) -> Customer:
    with get_session() as s:
        if customer_id:
            c = s.get(Customer, customer_id)
            if not c:
                raise ValueError("Cliente não encontrado")
            for k, v in data.items():
                setattr(c, k, v)
        else:
            c = Customer(**data)
            s.add(c)
        s.flush()
        s.refresh(c)
        return c


def delete_customer(customer_id: int):
    with get_session() as s:
        c = s.get(Customer, customer_id)
        if c:
            s.delete(c)


class CustomerFormDialog(QDialog):
    def __init__(self, customer: Customer | None = None, parent=None):
        super().__init__(parent)
        self._customer = customer
        self.setWindowTitle("Novo Cliente" if not customer else "Editar Cliente")
        self.setMinimumWidth(380)
        self._build_ui()
        if customer:
            self._populate(customer)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        form.addRow("Nome *", self.name_edit)

        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("(00) 00000-0000")
        form.addRow("Telefone", self.phone_edit)

        self.cpf_edit = QLineEdit()
        self.cpf_edit.setPlaceholderText("000.000.000-00")
        form.addRow("CPF", self.cpf_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("email@exemplo.com")
        form.addRow("E-mail", self.email_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        form.addRow("Observações", self.notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, c: Customer):
        self.name_edit.setText(c.name or "")
        self.phone_edit.setText(c.phone or "")
        self.cpf_edit.setText(c.cpf or "")
        self.email_edit.setText(getattr(c, "email", "") or "")
        self.notes_edit.setPlainText(c.notes or "")

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Atenção", "O nome é obrigatório.")
            return
        data = {
            "name": name,
            "phone": self.phone_edit.text().strip(),
            "cpf": self.cpf_edit.text().strip(),
            "email": self.email_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }
        try:
            save_customer(self._customer.id if self._customer else None, data)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))


class CustomersView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Clientes")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nome ou telefone...")
        self.search_edit.setFixedWidth(260)
        self.search_edit.textChanged.connect(self._load)
        header.addWidget(self.search_edit)

        add_btn = QPushButton("+ Novo Cliente")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add)
        header.addWidget(add_btn)

        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nome", "Telefone", "CPF", "Ações"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 140)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

    def _load(self):
        search = self.search_edit.text().strip()
        customers = list_customers(search)
        self.table.setRowCount(len(customers))
        for row, c in enumerate(customers):
            for col, text in enumerate([str(c.id), c.name, c.phone or "", c.cpf or ""]):
                self.table.setItem(row, col, QTableWidgetItem(text))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            hist_btn = QPushButton("Histórico")
            hist_btn.setObjectName("btn_primary")
            hist_btn.setFixedHeight(28)
            hist_btn.clicked.connect(lambda _, cid=c.id: self._history(cid))
            al.addWidget(hist_btn)

            edit_btn = QPushButton("Editar")
            edit_btn.setFixedHeight(28)
            edit_btn.clicked.connect(lambda _, cid=c.id: self._edit(cid))
            al.addWidget(edit_btn)

            del_btn = QPushButton("Excluir")
            del_btn.setObjectName("btn_danger")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, cid=c.id: self._delete(cid))
            al.addWidget(del_btn)

            self.table.setCellWidget(row, 4, actions)
            self.table.setRowHeight(row, 38)

    def _history(self, customer_id: int):
        with get_session() as s:
            c = s.get(Customer, customer_id)
        if not c:
            return
        from app.views.customers.customer_history_dialog import CustomerHistoryDialog
        dlg = CustomerHistoryDialog(c, parent=self)
        dlg.exec()

    def _add(self):
        dlg = CustomerFormDialog(parent=self)
        if dlg.exec():
            self._load()

    def _edit(self, customer_id: int):
        with get_session() as s:
            c = s.get(Customer, customer_id)
        if not c:
            return
        dlg = CustomerFormDialog(customer=c, parent=self)
        if dlg.exec():
            self._load()

    def _delete(self, customer_id: int):
        reply = QMessageBox.question(
            self, "Confirmar exclusão", "Excluir este cliente?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_customer(customer_id)
            self._load()
