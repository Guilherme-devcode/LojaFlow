"""Dashboard — landing page with today's overview."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.product_service import get_low_stock_products
from app.services.report_service import get_today_summary
from app.services.sale_service import list_sales


class _StatCard(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        self._value = QLabel("—")
        self._value.setObjectName("stat_value")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label = QLabel(title)
        self._label.setObjectName("stat_label")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._value)
        layout.addWidget(self._label)

    def set_value(self, text: str):
        self._value.setText(text)


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._navigate_to_pdv = None  # callable injected by main_window
        self._build_ui()
        self._load()

        # Refresh every 60s
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._load)
        self._timer.start(60_000)

    def set_navigate_callback(self, fn):
        """Allow main_window to inject navigation callback for the PDV button."""
        self._navigate_to_pdv = fn

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        header_row = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("page_title")
        header_row.addWidget(title)
        header_row.addStretch()

        self.date_label = QLabel(datetime.now().strftime("%A, %d de %B de %Y"))
        self.date_label.setObjectName("stat_label")
        header_row.addWidget(self.date_label)

        pdv_btn = QPushButton("Ir para PDV")
        pdv_btn.setObjectName("btn_primary")
        pdv_btn.setFixedHeight(36)
        pdv_btn.clicked.connect(self._go_pdv)
        header_row.addWidget(pdv_btn)
        layout.addLayout(header_row)

        # Stat cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        self.card_revenue = _StatCard("Receita Hoje")
        self.card_sales = _StatCard("Vendas Hoje")
        self.card_ticket = _StatCard("Ticket Médio")
        self.card_low_stock = _StatCard("Itens c/ Estoque Baixo")
        for card in [self.card_revenue, self.card_sales, self.card_ticket, self.card_low_stock]:
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # Bottom row: low stock + recent sales
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # Low stock panel
        low_stock_frame = QFrame()
        low_stock_frame.setObjectName("card")
        low_layout = QVBoxLayout(low_stock_frame)
        low_layout.setContentsMargins(16, 12, 16, 12)
        low_title = QLabel("Produtos com Estoque Baixo")
        low_title.setObjectName("stat_label")
        low_layout.addWidget(low_title)

        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(3)
        self.low_stock_table.setHorizontalHeaderLabels(["Produto", "Estoque", "Mínimo"])
        self.low_stock_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.low_stock_table.verticalHeader().setVisible(False)
        self.low_stock_table.setFrameShape(QFrame.Shape.NoFrame)
        self.low_stock_table.setFixedHeight(220)
        self.low_stock_table.horizontalHeader().setStretchLastSection(True)
        self.low_stock_table.setColumnWidth(0, 200)
        self.low_stock_table.setColumnWidth(1, 80)
        low_layout.addWidget(self.low_stock_table)
        bottom_row.addWidget(low_stock_frame, 1)

        # Recent sales panel
        recent_frame = QFrame()
        recent_frame.setObjectName("card")
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(16, 12, 16, 12)
        recent_title = QLabel("Últimas Vendas de Hoje")
        recent_title.setObjectName("stat_label")
        recent_layout.addWidget(recent_title)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(4)
        self.recent_table.setHorizontalHeaderLabels(["Venda #", "Hora", "Total", "Pagamento"])
        self.recent_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.setFrameShape(QFrame.Shape.NoFrame)
        self.recent_table.setFixedHeight(220)
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.setColumnWidth(0, 70)
        self.recent_table.setColumnWidth(1, 80)
        self.recent_table.setColumnWidth(2, 90)
        recent_layout.addWidget(self.recent_table)
        bottom_row.addWidget(recent_frame, 1)

        layout.addLayout(bottom_row)
        layout.addStretch()

    def _load(self):
        self.date_label.setText(datetime.now().strftime("%A, %d de %B de %Y"))

        # Today's summary
        summary = get_today_summary()
        self.card_revenue.set_value(f"R$ {summary.total_revenue:.2f}")
        self.card_sales.set_value(str(summary.num_sales))
        self.card_ticket.set_value(f"R$ {summary.avg_ticket:.2f}")

        # Low stock
        low = get_low_stock_products()
        self.card_low_stock.set_value(str(len(low)))
        self.low_stock_table.setRowCount(min(len(low), 10))
        for row, p in enumerate(low[:10]):
            self.low_stock_table.setItem(row, 0, QTableWidgetItem(p.name))
            qty_item = QTableWidgetItem(f"{p.stock_qty:.2f} {p.unit}")
            qty_item.setForeground(Qt.GlobalColor.red)
            self.low_stock_table.setItem(row, 1, qty_item)
            self.low_stock_table.setItem(row, 2, QTableWidgetItem(f"{p.min_stock:.1f}"))
            self.low_stock_table.setRowHeight(row, 30)

        # Recent sales today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)
        recent = list_sales(date_from=today_start, date_to=today_end)[:8]
        methods = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}
        self.recent_table.setRowCount(len(recent))
        for row, sale in enumerate(recent):
            self.recent_table.setItem(row, 0, QTableWidgetItem(f"#{sale.id}"))
            self.recent_table.setItem(row, 1, QTableWidgetItem(sale.created_at.strftime("%H:%M")))
            self.recent_table.setItem(row, 2, QTableWidgetItem(f"R$ {sale.total:.2f}"))
            self.recent_table.setItem(row, 3, QTableWidgetItem(methods.get(sale.payment_method, sale.payment_method)))
            self.recent_table.setRowHeight(row, 30)

    def _go_pdv(self):
        if self._navigate_to_pdv:
            self._navigate_to_pdv()
