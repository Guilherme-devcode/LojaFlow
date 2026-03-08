"""Product catalog view."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
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

from app.services.product_service import delete_product, get_product_by_id, list_products


class ProductsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_products()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Produtos")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar por nome ou código...")
        self.search_edit.setFixedWidth(280)
        self.search_edit.textChanged.connect(self._on_search_changed)
        header.addWidget(self.search_edit)

        add_btn = QPushButton("+ Novo Produto")
        add_btn.setObjectName("btn_primary")
        add_btn.clicked.connect(self._add_product)
        header.addWidget(add_btn)

        layout.addLayout(header)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nome", "Código de Barras", "Categoria",
            "Preço Venda", "Estoque", "Un.", "Ações"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 100)
        self.table.setColumnWidth(5, 80)
        self.table.setColumnWidth(6, 50)
        layout.addWidget(self.table)

        # Footer count
        self.count_label = QLabel("")
        self.count_label.setObjectName("stat_label")
        layout.addWidget(self.count_label)

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._load_products)

    def _on_search_changed(self):
        self._search_timer.start(300)

    def _load_products(self):
        search = self.search_edit.text().strip()
        products = list_products(search=search)

        self.table.setRowCount(len(products))
        for row, p in enumerate(products):
            items = [
                str(p.id),
                p.name,
                p.barcode or "",
                p.category.name if p.category else "",
                f"R$ {p.sale_price:.2f}",
                f"{p.stock_qty:.2f}",
                p.unit,
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if p.is_low_stock:
                    item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(row, col, item)

            # Actions cell
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)

            edit_btn = QPushButton("Editar")
            edit_btn.setFixedHeight(28)
            edit_btn.clicked.connect(lambda _, pid=p.id: self._edit_product(pid))
            actions_layout.addWidget(edit_btn)

            del_btn = QPushButton("Excluir")
            del_btn.setObjectName("btn_danger")
            del_btn.setFixedHeight(28)
            del_btn.clicked.connect(lambda _, pid=p.id: self._delete_product(pid))
            actions_layout.addWidget(del_btn)

            self.table.setCellWidget(row, 7, actions_widget)
            self.table.setRowHeight(row, 38)

        total = len(products)
        low = sum(1 for p in products if p.is_low_stock)
        msg = f"{total} produto(s) listado(s)"
        if low:
            msg += f"  •  ⚠ {low} com estoque baixo"
        self.count_label.setText(msg)

    def _add_product(self):
        from app.views.products.product_form import ProductFormDialog
        dlg = ProductFormDialog(parent=self)
        if dlg.exec():
            self._load_products()

    def _edit_product(self, product_id: int):
        product = get_product_by_id(product_id)
        if not product:
            return
        from app.views.products.product_form import ProductFormDialog
        dlg = ProductFormDialog(product=product, parent=self)
        if dlg.exec():
            self._load_products()

    def _delete_product(self, product_id: int):
        product = get_product_by_id(product_id)
        if not product:
            return
        reply = QMessageBox.question(
            self, "Confirmar exclusão",
            f"Excluir o produto '{product.name}'?\n(O produto será desativado, não apagado permanentemente)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            delete_product(product_id)
            self._load_products()
