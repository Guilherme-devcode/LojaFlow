"""Receipt printing via ESC/POS or Qt fallback."""
from __future__ import annotations

import textwrap
from datetime import datetime

from app.models.sale import Sale


def _format_receipt_lines(sale: Sale, store_name: str = "LojaFlow") -> list[str]:
    """Generate receipt lines (72-char width for standard thermal)."""
    W = 42  # thermal printer char width
    lines = []

    def center(text: str) -> str:
        return text.center(W)

    def divider(char: str = "-") -> str:
        return char * W

    lines.append(center(store_name))
    lines.append(center("CUPOM NÃO FISCAL"))
    lines.append(divider("="))
    lines.append(f"Data: {sale.created_at.strftime('%d/%m/%Y %H:%M')}")
    lines.append(f"Venda #: {sale.id}")
    lines.append(divider())

    for item in sale.items:
        name = textwrap.shorten(item.product_name, width=26, placeholder="...")
        qty_price = f"{item.qty:.2f} x R${item.unit_price:.2f}"
        subtotal = f"R${item.subtotal:.2f}"
        lines.append(f"{name:<26} {subtotal:>10}")
        lines.append(f"  {qty_price}")

    lines.append(divider())

    payment_labels = {"cash": "Dinheiro", "card": "Cartão", "pix": "Pix"}
    payment = payment_labels.get(sale.payment_method, sale.payment_method.capitalize())

    lines.append(f"{'Subtotal':<26} {'R$' + f'{sale.subtotal:.2f}':>10}")
    if sale.discount > 0:
        lines.append(f"{'Desconto':<26} {'-R$' + f'{sale.discount:.2f}':>10}")
    lines.append(f"{'TOTAL':<26} {'R$' + f'{sale.total:.2f}':>10}")
    lines.append(f"Pagamento: {payment}")
    if sale.payment_method == "cash" and sale.change_given > 0:
        lines.append(f"Troco: R${sale.change_given:.2f}")

    lines.append(divider("="))
    lines.append(center("Obrigado pela preferência!"))
    lines.append("")

    return lines


def print_receipt_escpos(sale: Sale, port: str = "USB", store_name: str = "LojaFlow") -> bool:
    """Print receipt using python-escpos. Returns True if successful."""
    try:
        from escpos import printer as ep

        if port.upper() == "USB":
            p = ep.Usb(0x04B8, 0x0202)  # Epson default; config can override
        elif port.startswith("/dev/") or port.upper().startswith("COM"):
            p = ep.Serial(port, baudrate=9600)
        else:
            p = ep.Network(port)

        lines = _format_receipt_lines(sale, store_name)
        for line in lines:
            p.text(line + "\n")
        p.cut()
        return True
    except Exception as exc:
        print(f"[printer_service] ESC/POS error: {exc}")
        return False


def print_receipt_qt(sale: Sale, store_name: str = "LojaFlow") -> bool:
    """Fallback: print via Qt printing dialog."""
    try:
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        from PySide6.QtWidgets import QApplication

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, QApplication.activeWindow())
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            return False

        lines = _format_receipt_lines(sale, store_name)
        html = "<pre style='font-family:monospace;font-size:10pt'>" + "\n".join(lines) + "</pre>"
        doc = QTextDocument()
        doc.setHtml(html)
        doc.print_(printer)
        return True
    except Exception as exc:
        print(f"[printer_service] Qt print error: {exc}")
        return False


def print_receipt(sale: Sale, port: str = "USB", store_name: str = "LojaFlow", use_escpos: bool = True) -> bool:
    if use_escpos:
        success = print_receipt_escpos(sale, port, store_name)
        if success:
            return True
    return print_receipt_qt(sale, store_name)
