"""Customer purchase history dialog."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.database import get_session
from app.models.customer import Customer
from app.models.sale import Sale
from app.services.sale_service import get_sale_by_id, list_sales


class CustomerHistoryDialog(QDialog):
    def __init__(self, customer: Customer, parent=None):
        super().__init__(parent)
        self._customer = customer
        self.setWindowTitle(f"Histórico — {customer.name}")
        self.setMinimumSize(620, 460)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Customer info header
        info_row = QHBoxLayout()
        name_lbl = QLabel(self._customer.name)
        name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0f172a;")
        info_row.addWidget(name_lbl)
        info_row.addStretch()

        phone_lbl = QLabel(self._customer.phone or "—")
        phone_lbl.setObjectName("stat_label")
        info_row.addWidget(phone_lbl)

        cpf_lbl = QLabel(self._customer.cpf or "—")
        cpf_lbl.setObjectName("stat_label")
        info_row.addWidget(cpf_lbl)
        layout.addLayout(info_row)

        # Summary stats
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("stat_label")
        layout.addWidget(self.summary_label)

        # Sales table
        sales_lbl = QLabel("Vendas Realizadas")
        sales_lbl.setObjectName("stat_label")
        layout.addWidget(sales_lbl)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Venda #", "Data/Hora", "Itens", "Total", "Pagamento"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 140)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 100)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table)

        hint = QLabel("Dê duplo clique para ver os detalhes da venda.")
        hint.setObjectName("stat_label")
        layout.addWidget(hint)

        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load(self):
        with get_session() as s:
            sales = (
                s.query(Sale)
                .filter(Sale.customer_id == self._customer.id)
                .order_by(Sale.created_at.desc())
                .all()
            )

        methods = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}
        completed = [sale for sale in sales if sale.status == "completed"]
        total_spent = sum(s.total for s in completed)

        self.summary_label.setText(
            f"{len(completed)} compra(s) concluída(s)  •  "
            f"Total gasto: R$ {total_spent:.2f}"
        )

        self.table.setRowCount(len(sales))
        for row, sale in enumerate(sales):
            is_cancelled = sale.status == "cancelled"
            method = methods.get(sale.payment_method, sale.payment_method)
            status_suffix = "  [CANCELADA]" if is_cancelled else ""
            row_data = [
                f"#{sale.id}",
                sale.created_at.strftime("%d/%m/%Y %H:%M"),
                str(len(sale.items)),
                f"R$ {sale.total:.2f}",
                f"{method}{status_suffix}",
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col != 1 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if is_cancelled:
                    item.setForeground(Qt.GlobalColor.darkGray)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, sale.id)
            self.table.setRowHeight(row, 34)

    def _open_detail(self):
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        sale_id = id_item.data(Qt.ItemDataRole.UserRole)
        sale = get_sale_by_id(sale_id)
        if not sale:
            return
        from app.views.sales.sale_detail_dialog import SaleDetailDialog
        dlg = SaleDetailDialog(sale, parent=self)
        dlg.exec()
        self._load()
