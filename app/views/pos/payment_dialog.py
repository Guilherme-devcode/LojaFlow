"""Payment dialog — method selection, change calculation, optional customer."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from app.database import get_session
from app.models.customer import Customer


class PaymentDialog(QDialog):
    def __init__(self, total: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Finalizar Venda")
        self.setMinimumWidth(380)
        self._total = total
        self.selected_method = "cash"
        self.amount_paid = total
        self.selected_customer_id: int | None = None
        self._customers: list[Customer] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Optional customer search
        customer_form = QFormLayout()
        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("Nome ou CPF (opcional)...")
        self.customer_edit.textChanged.connect(self._on_customer_search)
        customer_form.addRow("Cliente:", self.customer_edit)
        layout.addLayout(customer_form)

        self._customer_status = QLabel("")
        self._customer_status.setObjectName("stat_label")
        layout.addWidget(self._customer_status)

        self._load_customers()

        # Total display
        total_label = QLabel("Total a Pagar")
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(total_label)

        value_label = QLabel(f"R$ {self._total:.2f}")
        value_label.setObjectName("total_label")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Payment method
        method_label = QLabel("Forma de Pagamento:")
        layout.addWidget(method_label)

        method_widget = QWidget()
        method_layout = QHBoxLayout(method_widget)
        method_layout.setContentsMargins(0, 0, 0, 0)

        self._method_group = QButtonGroup(self)
        methods = [("Dinheiro", "cash"), ("Cartão", "card"), ("Pix", "pix")]
        self._method_radios: dict[str, QRadioButton] = {}
        for label, code in methods:
            radio = QRadioButton(label)
            if code == "cash":
                radio.setChecked(True)
            self._method_group.addButton(radio)
            method_layout.addWidget(radio)
            self._method_radios[code] = radio
            radio.toggled.connect(self._on_method_changed)

        layout.addWidget(method_widget)

        # Amount paid (for cash)
        form = QFormLayout()
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setPrefix("R$ ")
        self.amount_spin.setDecimals(2)
        self.amount_spin.setMaximum(999999.99)
        self.amount_spin.setValue(self._total)
        self.amount_spin.valueChanged.connect(self._update_change)
        form.addRow("Valor recebido:", self.amount_spin)

        self.change_label = QLabel("Troco: R$ 0,00")
        self.change_label.setObjectName("stat_value")
        form.addRow("", self.change_label)

        self._cash_widget = QWidget()
        self._cash_widget.setLayout(form)
        layout.addWidget(self._cash_widget)

        # Quick amount buttons
        quick_widget = QWidget()
        quick_layout = QHBoxLayout(quick_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        for amount in [5, 10, 20, 50, 100]:
            btn = QPushButton(f"R$ {amount}")
            btn.clicked.connect(lambda _, a=amount: self.amount_spin.setValue(self._round_up(a)))
            quick_layout.addWidget(btn)
        self._quick_widget = quick_widget
        layout.addWidget(quick_widget)

        # Confirm / Cancel
        buttons = QDialogButtonBox()
        confirm_btn = buttons.addButton("Confirmar Pagamento", QDialogButtonBox.ButtonRole.AcceptRole)
        confirm_btn.setObjectName("btn_success")
        buttons.addButton("Cancelar", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._confirm)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_change()

    def _load_customers(self):
        with get_session() as s:
            self._customers = s.query(Customer).order_by(Customer.name).all()
        names = [f"{c.name} ({c.cpf})" if c.cpf else c.name for c in self._customers]
        completer = QCompleter(names, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.customer_edit.setCompleter(completer)

    def _on_customer_search(self, text: str):
        text = text.strip().lower()
        if not text:
            self.selected_customer_id = None
            self._customer_status.setText("")
            return
        for c in self._customers:
            if text in c.name.lower() or (c.cpf and text in c.cpf):
                self.selected_customer_id = c.id
                self._customer_status.setText(f"✓ {c.name}")
                return
        self.selected_customer_id = None
        self._customer_status.setText("")

    def _round_up(self, amount: int) -> float:
        import math
        return math.ceil(self._total / amount) * amount

    def _on_method_changed(self):
        is_cash = self._method_radios["cash"].isChecked()
        self._cash_widget.setVisible(is_cash)
        self._quick_widget.setVisible(is_cash)
        if not is_cash:
            self.amount_spin.setValue(self._total)

    def _update_change(self):
        paid = self.amount_spin.value()
        change = max(0.0, paid - self._total)
        self.change_label.setText(f"Troco: R$ {change:.2f}")

    def _confirm(self):
        if self._method_radios["cash"].isChecked():
            paid = self.amount_spin.value()
            if paid < self._total:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Valor insuficiente",
                                    f"O valor recebido (R$ {paid:.2f}) é menor que o total (R$ {self._total:.2f}).")
                return
            self.selected_method = "cash"
            self.amount_paid = paid
        elif self._method_radios["card"].isChecked():
            self.selected_method = "card"
            self.amount_paid = self._total
        else:
            self.selected_method = "pix"
            self.amount_paid = self._total
        self.accept()
