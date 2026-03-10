"""Sales history view — list, filter, and inspect past sales."""
from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database import get_session
from app.models.sale import Sale
from app.services.sale_service import list_sales
from app.views.customers.customers_view import list_customers


class SalesHistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Histórico de Vendas")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        header.addWidget(QLabel("De:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-29))
        header.addWidget(self.date_from)

        header.addWidget(QLabel("Até:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        header.addWidget(self.date_to)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Apenas concluídas", "completed")
        self.status_combo.addItem("Todas (incl. canceladas)", "all")
        header.addWidget(self.status_combo)

        self.customer_combo = QComboBox()
        self.customer_combo.setFixedWidth(180)
        self.customer_combo.addItem("Todos os clientes", None)
        for c in list_customers():
            self.customer_combo.addItem(c.name, c.id)
        header.addWidget(QLabel("Cliente:"))
        header.addWidget(self.customer_combo)

        search_btn = QPushButton("Filtrar")
        search_btn.setObjectName("btn_primary")
        search_btn.clicked.connect(self._load)
        header.addWidget(search_btn)

        layout.addLayout(header)

        # Summary row
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("stat_label")
        layout.addWidget(self.summary_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Venda #", "Data/Hora", "Itens", "Subtotal", "Desconto", "Total", "Pagamento / Status"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(2, 60)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 90)
        self.table.setColumnWidth(6, 140)
        self.table.doubleClicked.connect(self._open_detail)
        layout.addWidget(self.table)

        hint = QLabel("Dê duplo clique em uma venda para ver detalhes e cancelar.")
        hint.setObjectName("stat_label")
        layout.addWidget(hint)

    def _load(self):
        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()
        dt_from = datetime.combine(d_from, datetime.min.time())
        dt_to = datetime.combine(d_to, datetime.max.time())

        include_cancelled = self.status_combo.currentData() == "all"
        customer_id = self.customer_combo.currentData()
        sales = list_sales(dt_from, dt_to, include_cancelled=include_cancelled, customer_id=customer_id)

        self.table.setRowCount(len(sales))
        total_revenue = 0.0
        methods = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}

        for row, sale in enumerate(sales):
            is_cancelled = sale.status == "cancelled"
            method_label = methods.get(sale.payment_method, sale.payment_method)
            status_label = f"{method_label}" if not is_cancelled else f"{method_label}  [CANCELADA]"

            row_data = [
                f"#{sale.id}",
                sale.created_at.strftime("%d/%m/%Y %H:%M"),
                str(len(sale.items)),
                f"R$ {sale.subtotal:.2f}",
                f"R$ {sale.discount:.2f}" if sale.discount > 0 else "—",
                f"R$ {sale.total:.2f}",
                status_label,
            ]
            for col, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col != 1 else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                if is_cancelled:
                    item.setForeground(Qt.GlobalColor.darkGray)
                self.table.setItem(row, col, item)

            # Store sale_id in first item for detail lookup
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, sale.id)
            self.table.setRowHeight(row, 34)

            if not is_cancelled:
                total_revenue += sale.total

        completed = sum(1 for s in sales if s.status == "completed")
        cancelled = sum(1 for s in sales if s.status == "cancelled")
        self.summary_label.setText(
            f"{completed} venda(s) concluída(s)  •  "
            f"{cancelled} cancelada(s)  •  "
            f"Total: R$ {total_revenue:.2f}"
        )

    def _open_detail(self):
        row = self.table.currentRow()
        id_item = self.table.item(row, 0)
        if not id_item:
            return
        sale_id = id_item.data(Qt.ItemDataRole.UserRole)

        with get_session() as s:
            sale = s.get(Sale, sale_id)
        if not sale:
            return

        from app.views.sales.sale_detail_dialog import SaleDetailDialog
        dlg = SaleDetailDialog(sale, parent=self)
        if dlg.exec():
            self._load()  # Refresh after possible cancellation
