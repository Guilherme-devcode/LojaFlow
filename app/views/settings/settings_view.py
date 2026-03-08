"""Application settings view."""
import hashlib

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.database import get_session
from app.models.user import User
from app.services.settings_service import get_config, set_config, invalidate_cache


class SettingsView(QWidget):
    def __init__(self, status_bar: QStatusBar | None = None, parent=None):
        super().__init__(parent)
        self._status_bar = status_bar
        self._build_ui()
        self._load()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(24, 16, 24, 16)
        main.setSpacing(20)

        title = QLabel("Configurações")
        title.setObjectName("page_title")
        main.addWidget(title)

        # ── Store info ────────────────────────────────────────────────────────
        store_group = QGroupBox("Dados da Loja")
        store_form = QFormLayout(store_group)
        store_form.setSpacing(10)

        self.store_name_edit = QLineEdit()
        store_form.addRow("Nome da loja:", self.store_name_edit)

        self.cnpj_edit = QLineEdit()
        self.cnpj_edit.setPlaceholderText("00.000.000/0000-00")
        store_form.addRow("CNPJ:", self.cnpj_edit)

        self.address_edit = QLineEdit()
        store_form.addRow("Endereço:", self.address_edit)

        self.phone_edit = QLineEdit()
        store_form.addRow("Telefone:", self.phone_edit)

        self.footer_edit = QLineEdit()
        self.footer_edit.setPlaceholderText("Mensagem no rodapé do cupom")
        store_form.addRow("Rodapé cupom:", self.footer_edit)

        save_store_btn = QPushButton("Salvar Dados da Loja")
        save_store_btn.setObjectName("btn_primary")
        save_store_btn.clicked.connect(self._save_store)
        store_form.addRow("", save_store_btn)

        main.addWidget(store_group)

        # ── Printer config ────────────────────────────────────────────────────
        printer_group = QGroupBox("Impressora Térmica (ESC/POS)")
        printer_form = QFormLayout(printer_group)
        printer_form.setSpacing(10)

        self.printer_port_edit = QLineEdit()
        self.printer_port_edit.setPlaceholderText("USB  ou  /dev/ttyUSB0  ou  COM3")
        printer_form.addRow("Porta / Conexão:", self.printer_port_edit)

        printer_row = QHBoxLayout()
        save_printer_btn = QPushButton("Salvar Impressora")
        save_printer_btn.setObjectName("btn_primary")
        save_printer_btn.clicked.connect(self._save_printer)
        printer_row.addWidget(save_printer_btn)

        test_printer_btn = QPushButton("Testar Impressão")
        test_printer_btn.clicked.connect(self._test_printer)
        printer_row.addWidget(test_printer_btn)
        printer_row.addStretch()
        printer_form.addRow("", printer_row)

        main.addWidget(printer_group)

        # ── User management ───────────────────────────────────────────────────
        user_group = QGroupBox("Alterar Senha do Administrador")
        user_form = QFormLayout(user_group)
        user_form.setSpacing(10)

        self.old_pass_edit = QLineEdit()
        self.old_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        user_form.addRow("Senha atual:", self.old_pass_edit)

        self.new_pass_edit = QLineEdit()
        self.new_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        user_form.addRow("Nova senha:", self.new_pass_edit)

        self.confirm_pass_edit = QLineEdit()
        self.confirm_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        user_form.addRow("Confirmar senha:", self.confirm_pass_edit)

        change_pass_btn = QPushButton("Alterar Senha")
        change_pass_btn.setObjectName("btn_warning")
        change_pass_btn.clicked.connect(self._change_password)
        user_form.addRow("", change_pass_btn)

        main.addWidget(user_group)

        # ── User management panel ─────────────────────────────────────────────
        from app.views.settings.user_management_view import UserManagementWidget
        self._user_mgmt = UserManagementWidget()
        main.addWidget(self._user_mgmt)

        # ── Backup ────────────────────────────────────────────────────────────
        backup_group = QGroupBox("Backup do Banco de Dados")
        backup_layout = QHBoxLayout(backup_group)
        backup_btn = QPushButton("Fazer Backup Agora")
        backup_btn.setObjectName("btn_primary")
        backup_btn.clicked.connect(self._do_backup)
        backup_layout.addWidget(backup_btn)
        self.backup_status = QLabel("")
        self.backup_status.setObjectName("stat_label")
        backup_layout.addWidget(self.backup_status, 1)
        main.addWidget(backup_group)

        main.addStretch()

        # App info
        info = QLabel("LojaFlow v1.1.0  •  Sistema de gestão para comércio  •  Offline-first")
        info.setObjectName("stat_label")
        main.addWidget(info)

    def _load(self):
        self.store_name_edit.setText(get_config("store_name", "Minha Loja"))
        self.cnpj_edit.setText(get_config("store_cnpj"))
        self.address_edit.setText(get_config("store_address"))
        self.phone_edit.setText(get_config("store_phone"))
        self.footer_edit.setText(get_config("receipt_footer", "Obrigado pela preferência!"))
        self.printer_port_edit.setText(get_config("printer_port", "USB"))

    def _save_store(self):
        set_config("store_name", self.store_name_edit.text().strip())
        set_config("store_cnpj", self.cnpj_edit.text().strip())
        set_config("store_address", self.address_edit.text().strip())
        set_config("store_phone", self.phone_edit.text().strip())
        set_config("receipt_footer", self.footer_edit.text().strip())
        invalidate_cache()
        QMessageBox.information(self, "Salvo", "Dados da loja salvos com sucesso.")
        if self._status_bar:
            self._status_bar.showMessage(f"Loja: {self.store_name_edit.text()}")

    def _save_printer(self):
        set_config("printer_port", self.printer_port_edit.text().strip())
        QMessageBox.information(self, "Salvo", "Configuração de impressora salva.")

    def _test_printer(self):
        from app.services.printer_service import print_receipt_escpos
        from app.models.sale import Sale, SaleItem
        from datetime import datetime

        # Create a dummy sale for test print
        fake_sale = Sale()
        fake_sale.id = 0
        fake_sale.total = 0.0
        fake_sale.subtotal = 0.0
        fake_sale.discount = 0.0
        fake_sale.payment_method = "cash"
        fake_sale.amount_paid = 0.0
        fake_sale.change_given = 0.0
        fake_sale.created_at = datetime.now()
        fake_sale.items = []

        store_name = get_config("store_name", "LojaFlow")
        port = get_config("printer_port", "USB")
        ok = print_receipt_escpos(fake_sale, port, store_name)
        if ok:
            QMessageBox.information(self, "Teste", "Impressão de teste enviada com sucesso.")
        else:
            QMessageBox.warning(self, "Falha", "Não foi possível imprimir. Verifique a porta e a impressora.")

    def _change_password(self):
        old = self.old_pass_edit.text()
        new = self.new_pass_edit.text()
        confirm = self.confirm_pass_edit.text()

        if not old or not new:
            QMessageBox.warning(self, "Atenção", "Preencha todos os campos.")
            return

        if new != confirm:
            QMessageBox.warning(self, "Atenção", "As senhas não coincidem.")
            return

        if len(new) < 4:
            QMessageBox.warning(self, "Atenção", "A nova senha deve ter pelo menos 4 caracteres.")
            return

        old_hash = hashlib.sha256(old.encode()).hexdigest()
        new_hash = hashlib.sha256(new.encode()).hexdigest()

        with get_session() as s:
            admin = s.query(User).filter_by(username="admin").first()
            if not admin or admin.password_hash != old_hash:
                QMessageBox.warning(self, "Erro", "Senha atual incorreta.")
                return
            admin.password_hash = new_hash

        QMessageBox.information(self, "Sucesso", "Senha alterada com sucesso.")
        self.old_pass_edit.clear()
        self.new_pass_edit.clear()
        self.confirm_pass_edit.clear()

    def _do_backup(self):
        from PySide6.QtWidgets import QFileDialog
        from app.services.backup_service import create_backup
        from pathlib import Path

        dest = QFileDialog.getExistingDirectory(self, "Selecionar pasta para backup")
        if not dest:
            return

        try:
            backup_path = create_backup(Path(dest))
            self.backup_status.setText(f"✓ Backup salvo: {backup_path.name}")
            QMessageBox.information(self, "Backup", f"Backup criado com sucesso:\n{backup_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Erro no Backup", str(exc))
