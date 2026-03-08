"""Main application window with sidebar navigation."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LojaFlow")
        self.setMinimumSize(1200, 750)
        self._current_user = None

        self._build_ui()
        self._navigate_to(0)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(8, 0, 8, 8)
        sidebar_layout.setSpacing(2)

        logo = QLabel("LojaFlow")
        logo.setObjectName("logo_label")
        sidebar_layout.addWidget(logo)

        version = QLabel("v1.0.0")
        version.setObjectName("version_label")
        sidebar_layout.addWidget(version)

        self._nav_buttons = []
        nav_items = [
            ("🛒  PDV", "Ponto de Venda"),
            ("📦  Produtos", "Catálogo de produtos"),
            ("📊  Estoque", "Controle de estoque"),
            ("📈  Relatórios", "Relatórios de vendas"),
            ("👤  Clientes", "Cadastro de clientes"),
            ("⚙️  Configurações", "Configurações do sistema"),
        ]

        for i, (label, _tooltip) in enumerate(nav_items):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setToolTip(_tooltip)
            btn.clicked.connect(lambda checked, idx=i: self._navigate_to(idx))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # ── Page stack ──
        self._stack = QStackedWidget()
        self._pages = []

        # Lazy-load pages to keep startup fast
        placeholders = [
            "PDV", "Produtos", "Estoque", "Relatórios", "Clientes", "Configurações"
        ]
        for name in placeholders:
            placeholder = QWidget()
            placeholder.setProperty("page_name", name)
            self._pages.append(placeholder)
            self._stack.addWidget(placeholder)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self._stack, 1)

        # ── Status bar ──
        status = QStatusBar()
        status.showMessage("LojaFlow iniciado  •  Banco de dados: OK")
        self.setStatusBar(status)
        self._status_bar = status

    def _navigate_to(self, index: int):
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)

        # Lazy-load the real page widget on first visit
        placeholder = self._pages[index]
        if placeholder.property("page_name") is not None:
            real_page = self._load_page(index)
            if real_page is not placeholder:
                self._stack.removeWidget(placeholder)
                self._stack.insertWidget(index, real_page)
                self._pages[index] = real_page

        self._stack.setCurrentIndex(index)

    def _load_page(self, index: int) -> QWidget:
        """Instantiate the real page widget for the given nav index."""
        if index == 0:
            from app.views.pos.pos_view import POSView
            return POSView()
        elif index == 1:
            from app.views.products.products_view import ProductsView
            return ProductsView()
        elif index == 2:
            from app.views.inventory.inventory_view import InventoryView
            return InventoryView()
        elif index == 3:
            from app.views.reports.reports_view import ReportsView
            return ReportsView()
        elif index == 4:
            from app.views.customers.customers_view import CustomersView
            return CustomersView()
        elif index == 5:
            from app.views.settings.settings_view import SettingsView
            return SettingsView(status_bar=self._status_bar)
        return self._pages[index]

    def set_status(self, message: str):
        self._status_bar.showMessage(message)
