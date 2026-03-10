"""Sale detail dialog — shows items and allows cancellation and reprinting."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.models.sale import Sale
from app.services.sale_service import cancel_sale


class SaleDetailDialog(QDialog):
    def __init__(self, sale: Sale, parent=None):
        super().__init__(parent)
        self._sale = sale
        self.setWindowTitle(f"Venda #{sale.id}")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header info
        methods = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}
        status_text = "✓ Concluída" if self._sale.status == "completed" else "✗ Cancelada"
        status_color = "#a6e3a1" if self._sale.status == "completed" else "#f38ba8"

        info_group = QGroupBox("Informações da Venda")
        info_layout = QHBoxLayout(info_group)

        def kv(label, value, color=None):
            col = QVBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("stat_label")
            val = QLabel(value)
            if color:
                val.setStyleSheet(f"color: {color}; font-weight: bold;")
            col.addWidget(lbl)
            col.addWidget(val)
            return col

        info_layout.addLayout(kv("Venda #", str(self._sale.id)))
        info_layout.addLayout(kv("Data", self._sale.created_at.strftime("%d/%m/%Y %H:%M")))
        info_layout.addLayout(kv("Status", status_text, status_color))
        info_layout.addLayout(kv("Pagamento", methods.get(self._sale.payment_method, "—")))
        info_layout.addLayout(kv("Total", f"R$ {self._sale.total:.2f}"))
        if self._sale.change_given > 0:
            info_layout.addLayout(kv("Troco", f"R$ {self._sale.change_given:.2f}"))

        layout.addWidget(info_group)

        # Items table
        items_label = QLabel("Itens")
        items_label.setObjectName("stat_label")
        layout.addWidget(items_label)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Produto", "Qtd.", "Preço Unit.", "Subtotal"])
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.horizontalHeader().setStretchLastSection(True)

        for row, item in enumerate(self._sale.items):
            self.items_table.insertRow(row)
            self.items_table.setItem(row, 0, QTableWidgetItem(item.product_name))
            self.items_table.setItem(row, 1, QTableWidgetItem(f"{item.qty:.3f}"))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"R$ {item.unit_price:.2f}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"R$ {item.subtotal:.2f}"))
            self.items_table.setRowHeight(row, 32)

        layout.addWidget(self.items_table)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reprint_btn = QPushButton("Reimprimir Recibo")
        reprint_btn.setObjectName("btn_warning")
        reprint_btn.setEnabled(self._sale.status == "completed")
        reprint_btn.clicked.connect(self._reprint)
        btn_layout.addWidget(reprint_btn)

        if self._sale.status == "completed":
            cancel_btn = QPushButton("Cancelar Venda")
            cancel_btn.setObjectName("btn_danger")
            cancel_btn.clicked.connect(self._cancel_sale)
            btn_layout.addWidget(cancel_btn)

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _reprint(self):
        from app.services.printer_service import print_receipt
        from app.services.settings_service import get_config
        port = get_config("printer_port", "USB")
        store_name = get_config("store_name", "LojaFlow")
        ok = print_receipt(self._sale, port=port, store_name=store_name)
        if not ok:
            QMessageBox.warning(self, "Impressão", "Não foi possível imprimir. Verifique a configuração da impressora.")

    def _cancel_sale(self):
        reason, ok = QInputDialog.getText(
            self, "Motivo do Cancelamento",
            "Informe o motivo do cancelamento (opcional):",
        )
        if not ok:
            return

        confirm = QMessageBox.question(
            self, "Confirmar Cancelamento",
            f"Cancelar a venda #{self._sale.id}?\n"
            "O estoque dos produtos será restaurado.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            cancel_sale(self._sale.id, reason)
            QMessageBox.information(self, "Cancelado",
                                    f"Venda #{self._sale.id} cancelada. Estoque restaurado.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))
