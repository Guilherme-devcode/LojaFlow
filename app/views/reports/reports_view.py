"""Sales reports view with Matplotlib charts."""
from datetime import date, timedelta

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.report_service import ReportData, get_report


class StatCard(QWidget):
    def __init__(self, title: str, value: str = "—", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("stat_value")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("stat_label")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        layout.addWidget(self.title_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._report: ReportData | None = None
        self._canvas = None
        self._build_ui()
        self._load_today()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        title = QLabel("Relatórios de Vendas")
        title.setObjectName("page_title")
        header.addWidget(title)
        header.addStretch()

        # Date range
        header.addWidget(QLabel("De:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-6))
        header.addWidget(self.date_from)

        header.addWidget(QLabel("Até:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        header.addWidget(self.date_to)

        search_btn = QPushButton("Gerar Relatório")
        search_btn.setObjectName("btn_primary")
        search_btn.clicked.connect(self._generate_report)
        header.addWidget(search_btn)

        today_btn = QPushButton("Hoje")
        today_btn.clicked.connect(self._load_today)
        header.addWidget(today_btn)

        export_btn = QPushButton("Exportar CSV")
        export_btn.setObjectName("btn_warning")
        export_btn.clicked.connect(self._export_csv)
        header.addWidget(export_btn)

        layout.addLayout(header)

        # Stat cards
        cards_layout = QHBoxLayout()
        self.card_revenue = StatCard("Receita Total")
        self.card_sales = StatCard("Vendas")
        self.card_ticket = StatCard("Ticket Médio")
        self.card_cash = StatCard("Dinheiro")
        self.card_card = StatCard("Cartão")
        self.card_pix = StatCard("Pix")
        for card in [self.card_revenue, self.card_sales, self.card_ticket,
                     self.card_cash, self.card_card, self.card_pix]:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            cards_layout.addWidget(card)
        layout.addLayout(cards_layout)

        # Chart + Table side by side
        content = QHBoxLayout()
        content.setSpacing(16)

        # Chart placeholder — populated after matplotlib import
        self.chart_container = QVBoxLayout()
        chart_frame = QFrame()
        chart_frame.setObjectName("card")
        chart_frame.setLayout(self.chart_container)
        chart_frame.setMinimumHeight(280)
        content.addWidget(chart_frame, 2)

        # Top products table
        table_layout = QVBoxLayout()
        top_label = QLabel("Top 10 Produtos")
        top_label.setObjectName("stat_label")
        table_layout.addWidget(top_label)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(3)
        self.products_table.setHorizontalHeaderLabels(["Produto", "Qtd.", "Receita"])
        self.products_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.products_table.setColumnWidth(1, 70)
        self.products_table.setColumnWidth(2, 90)
        table_layout.addWidget(self.products_table)

        table_frame = QFrame()
        table_frame.setObjectName("card")
        table_frame.setLayout(table_layout)
        content.addWidget(table_frame, 1)

        layout.addLayout(content, 1)

    def _load_today(self):
        self.date_from.setDate(QDate.currentDate())
        self.date_to.setDate(QDate.currentDate())
        self._generate_report()

    def _generate_report(self):
        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()
        if d_from > d_to:
            d_from, d_to = d_to, d_from

        self._report = get_report(d_from, d_to)
        self._update_cards()
        self._update_chart()
        self._update_table()

    def _update_cards(self):
        r = self._report
        self.card_revenue.set_value(f"R$ {r.total_revenue:.2f}")
        self.card_sales.set_value(str(r.num_sales))
        self.card_ticket.set_value(f"R$ {r.avg_ticket:.2f}")
        self.card_cash.set_value(f"R$ {r.by_payment.get('cash', 0):.2f}")
        self.card_card.set_value(f"R$ {r.by_payment.get('card', 0):.2f}")
        self.card_pix.set_value(f"R$ {r.by_payment.get('pix', 0):.2f}")

    def _update_chart(self):
        try:
            import matplotlib
            matplotlib.use("QtAgg")
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
        except ImportError:
            return

        # Clear old canvas
        while self.chart_container.count():
            item = self.chart_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        fig = Figure(figsize=(5, 3), facecolor="#ffffff")
        ax = fig.add_subplot(111)
        ax.set_facecolor("#ffffff")

        summaries = self._report.daily_summaries
        dates = [s.date.strftime("%d/%m") for s in summaries]
        totals = [s.total for s in summaries]

        bar_colors = ["#6366f1"] * len(dates)
        ax.bar(dates, totals, color=bar_colors, width=0.6,
               edgecolor="#4f46e5", linewidth=0.5)

        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#e2e8f0", linewidth=0.8, linestyle="-")
        ax.xaxis.grid(False)

        ax.spines["bottom"].set_color("#e2e8f0")
        ax.spines["left"].set_color("#e2e8f0")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_ylabel("R$", color="#64748b", fontsize=9)
        ax.set_title("Vendas por Dia", color="#0f172a", fontsize=11, fontweight="bold", pad=10)
        ax.tick_params(axis="x", colors="#0f172a", labelsize=9)
        ax.tick_params(axis="y", colors="#64748b", labelsize=9)

        if len(dates) > 10:
            ax.set_xticks(ax.get_xticks()[::max(1, len(dates) // 8)])

        fig.tight_layout(pad=1.5)

        canvas = FigureCanvasQTAgg(fig)
        self._canvas = canvas
        self.chart_container.addWidget(canvas)

    def _update_table(self):
        products = self._report.top_products
        self.products_table.setRowCount(len(products))
        for row, p in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(p.product_name))
            self.products_table.setItem(row, 1, QTableWidgetItem(f"{p.qty_sold:.2f}"))
            self.products_table.setItem(row, 2, QTableWidgetItem(f"R$ {p.revenue:.2f}"))
            self.products_table.setRowHeight(row, 32)

    def _export_csv(self):
        if self._report is None:
            self._generate_report()

        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from app.services.report_service import export_csv

        d_from = self.date_from.date().toPython()
        d_to = self.date_to.date().toPython()
        default_name = f"lojaflow_{d_from.strftime('%Y%m%d')}_{d_to.strftime('%Y%m%d')}.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", default_name, "Arquivo CSV (*.csv)"
        )
        if not filepath:
            return

        try:
            count = export_csv(d_from, d_to, filepath)
            QMessageBox.information(
                self, "Exportado",
                f"{count} linha(s) exportada(s) para:\n{filepath}"
            )
        except Exception as exc:
            QMessageBox.critical(self, "Erro ao exportar", str(exc))
