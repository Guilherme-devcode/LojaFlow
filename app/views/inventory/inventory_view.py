"""Inventory / stock control view."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.inventory_service import adjust_stock, list_movements, set_stock
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
        refresh_btn.clicked.connect(self._refresh_all)
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

        # Tabs: Estoque | Movimentações
        self.tabs = QTabWidget()

        # ── Tab 1: Stock table ────────────────────────────────────────────────
        stock_tab = QWidget()
        stock_layout = QVBoxLayout(stock_tab)
        stock_layout.setContentsMargins(0, 8, 0, 0)

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
        stock_layout.addWidget(self.table)
        self.tabs.addTab(stock_tab, "Posição do Estoque")

        # ── Tab 2: Movements ─────────────────────────────────────────────────
        mov_tab = QWidget()
        mov_layout = QVBoxLayout(mov_tab)
        mov_layout.setContentsMargins(0, 8, 0, 0)
        mov_layout.setSpacing(8)

        mov_filters = QHBoxLayout()
        self.mov_product_combo = QComboBox()
        self.mov_product_combo.setFixedWidth(220)
        self.mov_product_combo.currentIndexChanged.connect(self._load_movements)
        mov_filters.addWidget(QLabel("Produto:"))
        mov_filters.addWidget(self.mov_product_combo)

        self.mov_type_combo = QComboBox()
        self.mov_type_combo.addItem("Todos os tipos", "")
        self.mov_type_combo.addItem("Entrada (in)", "in")
        self.mov_type_combo.addItem("Saída (out)", "out")
        self.mov_type_combo.addItem("Ajuste", "adjustment")
        self.mov_type_combo.setFixedWidth(160)
        self.mov_type_combo.currentIndexChanged.connect(self._load_movements)
        mov_filters.addWidget(QLabel("Tipo:"))
        mov_filters.addWidget(self.mov_type_combo)
        mov_filters.addStretch()
        mov_layout.addLayout(mov_filters)

        self.mov_table = QTableWidget()
        self.mov_table.setColumnCount(7)
        self.mov_table.setHorizontalHeaderLabels([
            "Data/Hora", "Produto", "Tipo", "Antes", "Variação", "Depois", "Motivo"
        ])
        self.mov_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.mov_table.verticalHeader().setVisible(False)
        self.mov_table.setAlternatingRowColors(True)
        self.mov_table.horizontalHeader().setStretchLastSection(True)
        self.mov_table.setColumnWidth(0, 130)
        self.mov_table.setColumnWidth(1, 180)
        self.mov_table.setColumnWidth(2, 80)
        self.mov_table.setColumnWidth(3, 70)
        self.mov_table.setColumnWidth(4, 80)
        self.mov_table.setColumnWidth(5, 70)
        mov_layout.addWidget(self.mov_table)
        self.tabs.addTab(mov_tab, "Movimentações")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)

    def _on_tab_changed(self, index: int):
        if index == 1:
            self._populate_product_combo()
            self._load_movements()

    def _populate_product_combo(self):
        self.mov_product_combo.blockSignals(True)
        self.mov_product_combo.clear()
        self.mov_product_combo.addItem("Todos os produtos", None)
        for p in list_products(active_only=False):
            self.mov_product_combo.addItem(p.name, p.id)
        self.mov_product_combo.blockSignals(False)

    def _load_movements(self):
        product_id = self.mov_product_combo.currentData()
        type_filter = self.mov_type_combo.currentData()
        movements = list_movements(product_id=product_id, limit=300)
        if type_filter:
            movements = [m for m in movements if m.movement_type == type_filter]

        type_labels = {"in": "Entrada", "out": "Saída", "adjustment": "Ajuste"}
        self.mov_table.setRowCount(len(movements))
        for row, m in enumerate(movements):
            qty_change = m.qty_change
            change_text = f"+{qty_change:.3f}" if qty_change >= 0 else f"{qty_change:.3f}"
            row_data = [
                m.created_at.strftime("%d/%m/%Y %H:%M"),
                m.product.name if m.product else "—",
                type_labels.get(m.movement_type, m.movement_type),
                f"{m.qty_before:.3f}",
                change_text,
                f"{m.qty_after:.3f}",
                m.reason or "—",
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col != 6 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                # Color the change column
                if col == 4:
                    item.setForeground(QColor("#10b981") if qty_change >= 0 else QColor("#ef4444"))
                self.mov_table.setItem(row, col, item)
            self.mov_table.setRowHeight(row, 32)

    def _refresh_all(self):
        self._load_products()
        if self.tabs.currentIndex() == 1:
            self._load_movements()

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
                    item.setForeground(QColor("#ef4444"))
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
