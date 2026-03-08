"""Inventory / stock control view."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.inventory_service import adjust_stock, set_stock
from app.services.product_service import get_product_by_id, list_products


class StockAdjustDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self._product = product
        self.setWindowTitle(f"Ajustar Estoque — {product.name}")
        self.setMinimumWidth(340)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        info = QLabel(f"Estoque atual: <b>{self._product.stock_qty:.3f} {self._product.unit}</b>")
        layout.addWidget(info)

        form = QFormLayout()

        self.new_qty_spin = QDoubleSpinBox()
        self.new_qty_spin.setDecimals(3)
        self.new_qty_spin.setMaximum(999999.0)
        self.new_qty_spin.setValue(self._product.stock_qty)
        form.addRow("Novo estoque:", self.new_qty_spin)

        self.reason_edit = QLineEdit()
        self.reason_edit.setPlaceholderText("Motivo do ajuste...")
        form.addRow("Motivo:", self.reason_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        new_qty = self.new_qty_spin.value()
        reason = self.reason_edit.text().strip() or "Ajuste manual"
        try:
            set_stock(self._product.id, new_qty, reason)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", str(exc))


class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_products()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Estoque")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar produto...")
        self.search_edit.setFixedWidth(240)
        self.search_edit.textChanged.connect(self._load_products)
        header.addWidget(self.search_edit)

        refresh_btn = QPushButton("Atualizar")
        refresh_btn.clicked.connect(self._load_products)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        # Stats row
        stats = QHBoxLayout()
        self.total_label = QLabel()
        self.low_label = QLabel()
        for lbl in [self.total_label, self.low_label]:
            lbl.setObjectName("stat_label")
            stats.addWidget(lbl)
        stats.addStretch()
        layout.addLayout(stats)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Produto", "Código", "Categoria", "Estoque", "Un.", "Mínimo", "Status", "Ações"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 50)
        self.table.setColumnWidth(5, 70)
        self.table.setColumnWidth(6, 90)
        layout.addWidget(self.table)

    def _load_products(self):
        search = self.search_edit.text().strip()
        products = list_products(search=search, active_only=True)

        low_stock = [p for p in products if p.is_low_stock]
        self.total_label.setText(f"Total: {len(products)} produtos")
        self.low_label.setText(f"⚠  Estoque baixo: {len(low_stock)} itens")

        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            status = "⚠ Baixo" if p.is_low_stock else "✓ OK"
            row_data = [
                p.name,
                p.barcode or "—",
                p.category.name if p.category else "—",
                f"{p.stock_qty:.3f}",
                p.unit,
                f"{p.min_stock:.1f}",
                status,
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col > 1 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if p.is_low_stock:
                    item.setForeground(QColor("#f38ba8"))
                self.table.setItem(row, col, item)

            adjust_btn = QPushButton("Ajustar")
            adjust_btn.setObjectName("btn_warning")
            adjust_btn.setFixedHeight(30)
            adjust_btn.clicked.connect(lambda _, pid=p.id: self._adjust_stock(pid))
            self.table.setCellWidget(row, 7, adjust_btn)
            self.table.setRowHeight(row, 36)

    def _adjust_stock(self, product_id: int):
        product = get_product_by_id(product_id)
        if not product:
            return
        dlg = StockAdjustDialog(product, parent=self)
        if dlg.exec():
            self._load_products()
