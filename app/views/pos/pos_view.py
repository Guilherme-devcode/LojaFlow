"""Point of Sale (PDV) screen."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.sale_service import Cart, CartItem, add_product_to_cart, finalize_sale


class POSView(QWidget):
    sale_completed = Signal(int)  # emits sale_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cart = Cart()
        self._build_ui()
        self._register_shortcuts()
        self.barcode_input.setFocus()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)

        # ── LEFT: Cart ───────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(10)

        title = QLabel("PDV — Ponto de Venda")
        title.setObjectName("page_title")
        left.addWidget(title)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["Produto", "Un.", "Qtd.", "Preço", "Subtotal", ""])
        self.cart_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.cart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cart_table.setColumnWidth(1, 50)
        self.cart_table.setColumnWidth(2, 70)
        self.cart_table.setColumnWidth(3, 90)
        self.cart_table.setColumnWidth(4, 90)
        self.cart_table.setColumnWidth(5, 60)
        left.addWidget(self.cart_table, 1)

        # Discount row
        discount_row = QHBoxLayout()
        discount_row.addWidget(QLabel("Desconto (R$):"))
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setPrefix("R$ ")
        self.discount_spin.setDecimals(2)
        self.discount_spin.setMaximum(99999.99)
        self.discount_spin.valueChanged.connect(self._update_totals)
        discount_row.addWidget(self.discount_spin)
        discount_row.addStretch()
        left.addLayout(discount_row)

        root.addLayout(left, 3)

        # ── RIGHT: Barcode + Totals + Controls ───────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(8)

        scan_label = QLabel("Código de Barras / Nome do Produto  [F2]")
        scan_label.setObjectName("stat_label")
        right.addWidget(scan_label)

        self.barcode_input = QLineEdit()
        self.barcode_input.setObjectName("barcode_input")
        self.barcode_input.setPlaceholderText("Scanner, código ou nome do produto...")
        self.barcode_input.returnPressed.connect(self._on_barcode_entered)
        self.barcode_input.textChanged.connect(self._on_search_text_changed)
        right.addWidget(self.barcode_input)

        # Search results popup list (hidden by default)
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(160)
        self.search_results.hide()
        self.search_results.itemClicked.connect(self._on_search_result_selected)
        right.addWidget(self.search_results)

        scan_btn = QPushButton("Adicionar  [Enter]")
        scan_btn.setObjectName("btn_primary")
        scan_btn.clicked.connect(self._on_barcode_entered)
        right.addWidget(scan_btn)

        right.addSpacerItem(QSpacerItem(0, 12, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Totals card
        totals_label = QLabel("Subtotal:")
        right.addWidget(totals_label)
        self.subtotal_label = QLabel("R$ 0,00")
        self.subtotal_label.setObjectName("stat_label")
        right.addWidget(self.subtotal_label)

        right.addWidget(QLabel("Total:"))
        self.total_label = QLabel("R$ 0,00")
        self.total_label.setObjectName("total_label")
        right.addWidget(self.total_label)

        right.addStretch()

        # Action buttons
        pay_btn = QPushButton("💳  Finalizar Venda  [F12]")
        pay_btn.setObjectName("btn_success")
        pay_btn.setMinimumHeight(50)
        pay_btn.clicked.connect(self._finalize_sale)
        right.addWidget(pay_btn)

        clear_btn = QPushButton("🗑  Limpar Carrinho")
        clear_btn.setObjectName("btn_danger")
        clear_btn.clicked.connect(self._clear_cart)
        right.addWidget(clear_btn)

        root.addLayout(right, 1)

    def _register_shortcuts(self):
        """Register keyboard shortcuts for common POS actions."""
        QShortcut(QKeySequence("F2"), self).activated.connect(
            lambda: self.barcode_input.setFocus()
        )
        QShortcut(QKeySequence("F12"), self).activated.connect(self._finalize_sale)
        QShortcut(QKeySequence("Escape"), self).activated.connect(
            lambda: (self.barcode_input.clear(), self.search_results.hide())
        )
        QShortcut(QKeySequence("Delete"), self).activated.connect(self._delete_selected_item)

    def _delete_selected_item(self):
        rows = self.cart_table.selectedItems()
        if not rows:
            return
        row = self.cart_table.currentRow()
        if 0 <= row < len(self._cart.items):
            product_id = self._cart.items[row].product_id
            self._remove_item(product_id)

    def _on_search_text_changed(self, text: str):
        """Show product name suggestions when text contains letters."""
        text = text.strip()
        if not text or text.isdigit() or len(text) < 2:
            self.search_results.hide()
            return

        from app.services.product_service import list_products
        products = list_products(search=text, active_only=True)[:6]
        if not products:
            self.search_results.hide()
            return

        self.search_results.clear()
        for p in products:
            label = f"{p.name}  •  R$ {p.sale_price:.2f}  •  {p.stock_qty:.0f} {p.unit}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.search_results.addItem(item)
        self.search_results.show()

    def _on_search_result_selected(self, list_item: QListWidgetItem):
        product_id = list_item.data(Qt.ItemDataRole.UserRole)
        self.search_results.hide()
        self.barcode_input.clear()
        self._add_by_id(str(product_id))

    def _add_by_id(self, code: str):
        item = add_product_to_cart(self._cart, code)
        if item is None:
            QMessageBox.warning(self, "Produto não encontrado",
                                f"Nenhum produto encontrado para: '{code}'")
        else:
            self._refresh_cart_table()
        self.barcode_input.setFocus()

    def _on_barcode_entered(self):
        code = self.barcode_input.text().strip()
        if not code:
            return

        self.search_results.hide()

        # If there are visible search results and Enter is pressed, pick first
        if self.search_results.count() > 0 and not code.isdigit():
            first = self.search_results.item(0)
            if first:
                self._on_search_result_selected(first)
                return

        item = add_product_to_cart(self._cart, code)
        if item is None:
            QMessageBox.warning(self, "Produto não encontrado",
                                f"Nenhum produto encontrado para: '{code}'")
            self.barcode_input.clear()
            return

        self.barcode_input.clear()
        self._refresh_cart_table()

    def _refresh_cart_table(self):
        self._cart.discount = self.discount_spin.value()
        self.cart_table.setRowCount(len(self._cart.items))

        for row, item in enumerate(self._cart.items):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item.product_name))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item.unit))

            qty_spin = QDoubleSpinBox()
            qty_spin.setDecimals(3)
            qty_spin.setMinimum(0.001)
            qty_spin.setMaximum(9999.0)
            qty_spin.setValue(item.qty)
            qty_spin.valueChanged.connect(lambda val, r=row: self._on_qty_changed(r, val))
            self.cart_table.setCellWidget(row, 2, qty_spin)

            self.cart_table.setItem(row, 3, QTableWidgetItem(f"R$ {item.unit_price:.2f}"))
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"R$ {item.subtotal:.2f}"))

            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("btn_danger")
            remove_btn.setFixedSize(30, 30)
            remove_btn.clicked.connect(lambda _, pid=item.product_id: self._remove_item(pid))
            self.cart_table.setCellWidget(row, 5, remove_btn)
            self.cart_table.setRowHeight(row, 40)

        self._update_totals()

    def _on_qty_changed(self, row: int, new_qty: float):
        if row < len(self._cart.items):
            self._cart.items[row].qty = round(new_qty, 3)
            item = self._cart.items[row]
            sub_item = self.cart_table.item(row, 4)
            if sub_item:
                sub_item.setText(f"R$ {item.subtotal:.2f}")
        self._update_totals()

    def _remove_item(self, product_id: int):
        self._cart.remove(product_id)
        self._refresh_cart_table()

    def _update_totals(self):
        self._cart.discount = self.discount_spin.value()
        self.subtotal_label.setText(f"R$ {self._cart.subtotal:.2f}")
        self.total_label.setText(f"R$ {self._cart.total:.2f}")

    def _clear_cart(self):
        if not self._cart.items:
            return
        reply = QMessageBox.question(
            self, "Limpar carrinho",
            "Remover todos os itens do carrinho?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cart.clear()
            self.discount_spin.setValue(0.0)
            self._refresh_cart_table()

    def _finalize_sale(self):
        if not self._cart.items:
            QMessageBox.information(self, "Carrinho vazio", "Adicione produtos antes de finalizar.")
            return

        from app.session import Session
        from app.views.pos.payment_dialog import PaymentDialog
        dlg = PaymentDialog(total=self._cart.total, parent=self)
        if dlg.exec():
            try:
                user_id = Session.current_user.id if Session.current_user else None
                sale = finalize_sale(
                    cart=self._cart,
                    payment_method=dlg.selected_method,
                    amount_paid=dlg.amount_paid,
                    customer_id=dlg.selected_customer_id,
                    user_id=user_id,
                )
                self.sale_completed.emit(sale.id)
                self._show_sale_success(sale)
                self._cart.clear()
                self.discount_spin.setValue(0.0)
                self._refresh_cart_table()
                self.barcode_input.setFocus()
            except Exception as exc:
                QMessageBox.critical(self, "Erro ao finalizar venda", str(exc))

    def _show_sale_success(self, sale):
        methods = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}
        msg = (
            f"Venda #{sale.id} finalizada!\n\n"
            f"Total: R$ {sale.total:.2f}\n"
            f"Pagamento: {methods.get(sale.payment_method, sale.payment_method)}\n"
        )
        if sale.payment_method == "cash" and sale.change_given > 0:
            msg += f"Troco: R$ {sale.change_given:.2f}\n"

        QMessageBox.information(self, "Venda Concluída", msg)

        print_reply = QMessageBox.question(
            self, "Imprimir cupom?", "Deseja imprimir o cupom?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if print_reply == QMessageBox.StandardButton.Yes:
            from app.database import get_session
            from app.models.sale import Sale as SaleModel
            from app.services import printer_service
            from app.services.settings_service import get_config
            with get_session() as s:
                full_sale = s.get(SaleModel, sale.id)
                if full_sale:
                    store_name = get_config("store_name", "LojaFlow")
                    port = get_config("printer_port", "USB")
                    printer_service.print_receipt(full_sale, port=port, store_name=store_name)
