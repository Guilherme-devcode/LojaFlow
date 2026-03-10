"""Main application window with sidebar navigation."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.session import Session


# Pages that require admin role (by nav index)
# 0=Dashboard, 1=PDV, 2=Produtos, 3=Vendas, 4=Estoque, 5=Relatórios, 6=Clientes, 7=Configurações
_ADMIN_ONLY_PAGES = {4, 5, 7}  # Estoque, Relatórios, Configurações


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        user_name = Session.current_user.name if Session.current_user else "—"
        self.setWindowTitle(f"LojaFlow — {user_name}")
        self.setMinimumSize(1200, 750)

        self._build_ui()
        self._apply_role_visibility()
        self._navigate_to(0)

        # Periodic low-stock badge refresh (every 60s)
        self._badge_timer = QTimer()
        self._badge_timer.timeout.connect(self._refresh_stock_badge)
        self._badge_timer.start(60_000)
        self._refresh_stock_badge()

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
        sidebar_layout.setContentsMargins(0, 0, 8, 12)
        sidebar_layout.setSpacing(2)

        logo = QLabel("LojaFlow")
        logo.setObjectName("logo_label")
        sidebar_layout.addWidget(logo)

        user_name = Session.current_user.name if Session.current_user else "—"
        user_role = Session.current_user.role if Session.current_user else ""

        user_badge = QLabel(user_name)
        user_badge.setObjectName("user_badge")
        sidebar_layout.addWidget(user_badge)

        role_map = {"admin": "Administrador", "cashier": "Operador de Caixa"}
        role_label = QLabel(role_map.get(user_role, user_role.capitalize()))
        role_label.setObjectName("user_role_badge")
        sidebar_layout.addWidget(role_label)

        divider_top = QFrame()
        divider_top.setObjectName("sidebar_separator")
        divider_top.setFixedHeight(1)
        sidebar_layout.addWidget(divider_top)
        sidebar_layout.addSpacing(6)

        self._nav_buttons: list[QPushButton] = []
        self._stock_badge: QLabel | None = None

        nav_items = [
            ("  Dashboard", "Visão geral do negócio"),
            ("  PDV", "Ponto de Venda"),
            ("  Produtos", "Catálogo de produtos"),
            ("  Vendas", "Histórico de vendas"),
            ("  Estoque", "Controle de estoque"),
            ("  Relatórios", "Relatórios e análises"),
            ("  Clientes", "Cadastro de clientes"),
            ("  Configurações", "Configurações do sistema"),
        ]

        for i, (label, _tooltip) in enumerate(nav_items):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)

            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setToolTip(_tooltip)
            btn.clicked.connect(lambda checked, idx=i: self._navigate_to(idx))
            row_layout.addWidget(btn, 1)

            # Low-stock badge (only on Estoque button, index 4)
            if i == 4:
                badge = QLabel()
                badge.setFixedSize(22, 22)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(
                    "background:#ef4444; color:#ffffff; border-radius:11px; font-size:11px; font-weight:bold;"
                )
                badge.hide()
                row_layout.addWidget(badge)
                self._stock_badge = badge

            sidebar_layout.addWidget(row_widget)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        divider_bottom = QFrame()
        divider_bottom.setObjectName("sidebar_separator")
        divider_bottom.setFixedHeight(1)
        sidebar_layout.addWidget(divider_bottom)
        sidebar_layout.addSpacing(6)

        # Logout button
        logout_btn = QPushButton("  Sair")
        logout_btn.setObjectName("sidebar_logout")
        logout_btn.clicked.connect(self._logout)
        sidebar_layout.addWidget(logout_btn)

        # ── Page stack ──
        self._stack = QStackedWidget()
        self._pages: list[QWidget] = []

        # Lazy-load placeholders
        page_names = ["Dashboard", "PDV", "Produtos", "Vendas", "Estoque", "Relatórios", "Clientes", "Configurações"]
        for name in page_names:
            placeholder = QWidget()
            placeholder.setProperty("page_name", name)
            self._pages.append(placeholder)
            self._stack.addWidget(placeholder)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self._stack, 1)

        # ── Status bar ──
        status = QStatusBar()
        user_info = f"Usuário: {Session.current_user.name} ({Session.current_user.role})" if Session.current_user else ""
        status.showMessage(f"LojaFlow  •  {user_info}  •  Banco de dados: OK")
        self.setStatusBar(status)
        self._status_bar = status

    def _apply_role_visibility(self):
        """Hide admin-only pages from cashiers."""
        if Session.is_admin():
            return
        for idx in _ADMIN_ONLY_PAGES:
            if idx < len(self._nav_buttons):
                self._nav_buttons[idx].parentWidget().setVisible(False)

    def _navigate_to(self, index: int):
        # Block restricted pages for cashiers
        if index in _ADMIN_ONLY_PAGES and not Session.is_admin():
            QMessageBox.warning(self, "Acesso negado",
                                "Esta área é restrita a administradores.")
            return

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
            from app.views.dashboard.dashboard_view import DashboardView
            view = DashboardView()
            view.set_navigate_callback(lambda: self._navigate_to(1))
            return view
        elif index == 1:
            from app.views.pos.pos_view import POSView
            view = POSView()
            view.sale_completed.connect(self._on_sale_completed)
            return view
        elif index == 2:
            from app.views.products.products_view import ProductsView
            return ProductsView()
        elif index == 3:
            from app.views.sales.sales_history_view import SalesHistoryView
            return SalesHistoryView()
        elif index == 4:
            from app.views.inventory.inventory_view import InventoryView
            return InventoryView()
        elif index == 5:
            from app.views.reports.reports_view import ReportsView
            return ReportsView()
        elif index == 6:
            from app.views.customers.customers_view import CustomersView
            return CustomersView()
        elif index == 7:
            from app.views.settings.settings_view import SettingsView
            return SettingsView(status_bar=self._status_bar)
        return self._pages[index]

    def _on_sale_completed(self, sale_id: int):
        self._refresh_stock_badge()

    def _refresh_stock_badge(self):
        """Update low-stock badge count on the Estoque nav button."""
        if self._stock_badge is None:
            return
        try:
            from app.services.product_service import get_low_stock_products
            low = get_low_stock_products()
            count = len(low)
            if count > 0:
                self._stock_badge.setText(str(count))
                self._stock_badge.show()
            else:
                self._stock_badge.hide()
        except Exception:
            pass

    def _logout(self):
        reply = QMessageBox.question(
            self, "Sair", "Deseja encerrar a sessão?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            Session.logout()
            self.close()

    def set_status(self, message: str):
        self._status_bar.showMessage(message)
