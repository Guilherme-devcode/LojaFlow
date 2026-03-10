"""Dialog for adding / editing a product."""
from PySide6.QtCore import Qt
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
    QVBoxLayout,
)

from app.models.product import Product
from app.services.product_service import (
    create_product,
    get_or_create_category,
    list_categories,
    update_product,
)


class ProductFormDialog(QDialog):
    def __init__(self, product: Product | None = None, parent=None):
        super().__init__(parent)
        self._product = product
        self.setWindowTitle("Novo Produto" if not product else "Editar Produto")
        self.setMinimumWidth(420)
        self._build_ui()
        if product:
            self._populate(product)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Novo Produto" if not self._product else "Editar Produto")
        title.setObjectName("page_title")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Nome do produto")
        form.addRow("Nome *", self.name_edit)

        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("EAN-13 ou interno")
        form.addRow("Código de barras", self.barcode_edit)

        # Category combo + quick add
        cat_layout = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItem("— Sem categoria —", None)
        for cat in list_categories():
            self.category_combo.addItem(cat.name, cat.id)
        cat_layout.addWidget(self.category_combo, 1)
        form.addRow("Categoria", cat_layout)

        self.sale_price_spin = QDoubleSpinBox()
        self.sale_price_spin.setPrefix("R$ ")
        self.sale_price_spin.setDecimals(2)
        self.sale_price_spin.setMaximum(999999.99)
        form.addRow("Preço de venda *", self.sale_price_spin)

        self.cost_price_spin = QDoubleSpinBox()
        self.cost_price_spin.setPrefix("R$ ")
        self.cost_price_spin.setDecimals(2)
        self.cost_price_spin.setMaximum(999999.99)
        form.addRow("Preço de custo", self.cost_price_spin)

        self.stock_spin = QDoubleSpinBox()
        self.stock_spin.setDecimals(3)
        self.stock_spin.setMaximum(999999.0)
        form.addRow("Estoque inicial", self.stock_spin)

        self.min_stock_spin = QDoubleSpinBox()
        self.min_stock_spin.setDecimals(1)
        self.min_stock_spin.setMaximum(9999.0)
        self.min_stock_spin.setValue(5.0)
        form.addRow("Estoque mínimo", self.min_stock_spin)

        self.unit_combo = QComboBox()
        for unit in ["un", "kg", "lt", "cx", "pc", "par"]:
            self.unit_combo.addItem(unit)
        form.addRow("Unidade", self.unit_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, product: Product):
        self.name_edit.setText(product.name)
        self.barcode_edit.setText(product.barcode or "")
        self.sale_price_spin.setValue(product.sale_price)
        self.cost_price_spin.setValue(product.cost_price)
        self.stock_spin.setValue(product.stock_qty)
        self.min_stock_spin.setValue(product.min_stock)
        idx = self.unit_combo.findText(product.unit)
        if idx >= 0:
            self.unit_combo.setCurrentIndex(idx)
        if product.category_id is not None:
            for i in range(self.category_combo.count()):
                if self.category_combo.itemData(i) == product.category_id:
                    self.category_combo.setCurrentIndex(i)
                    break

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Atenção", "O nome do produto é obrigatório.")
            return

        sale_price = self.sale_price_spin.value()
        if sale_price <= 0:
            QMessageBox.warning(self, "Atenção", "O preço de venda deve ser maior que zero.")
            return

        cat_name = self.category_combo.currentText().strip()
        category_id = None
        if cat_name and cat_name != "— Sem categoria —":
            cat = get_or_create_category(cat_name)
            category_id = cat.id

        data = {
            "name": name,
            "barcode": self.barcode_edit.text().strip() or None,
            "sale_price": sale_price,
            "cost_price": self.cost_price_spin.value(),
            "stock_qty": self.stock_spin.value(),
            "min_stock": self.min_stock_spin.value(),
            "unit": self.unit_combo.currentText(),
            "category_id": category_id,
        }

        try:
            if self._product:
                update_product(self._product.id, data)
            else:
                create_product(data)
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Erro", f"Não foi possível salvar:\n{exc}")
