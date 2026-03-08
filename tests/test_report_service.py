"""Tests for report service."""
import os
import tempfile
from datetime import date

import pytest

_tmpdir = tempfile.mkdtemp()
os.environ["LOJAFLOW_DATA"] = _tmpdir

from app.database import init_db
from app.services.product_service import create_product
from app.services.sale_service import Cart, CartItem, finalize_sale
from app.services.report_service import get_report, get_today_summary


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _make_sale(price: float, qty: float = 1.0, method: str = "cash"):
    p = create_product({"name": f"Produto R${price}", "sale_price": price, "stock_qty": 100.0})
    cart = Cart()
    cart.add_or_increment(CartItem(product_id=p.id, product_name=p.name, unit_price=price, qty=qty))
    return finalize_sale(cart, payment_method=method, amount_paid=price * qty)


class TestGetReport:
    def test_empty_report(self):
        report = get_report(date(2000, 1, 1), date(2000, 1, 1))
        assert report.num_sales == 0
        assert report.total_revenue == 0.0
        assert report.avg_ticket == 0.0

    def test_single_sale_today(self):
        _make_sale(50.0)
        report = get_today_summary()
        assert report.num_sales >= 1
        assert report.total_revenue >= 50.0

    def test_payment_breakdown(self):
        _make_sale(10.0, method="cash")
        _make_sale(20.0, method="card")
        _make_sale(15.0, method="pix")
        report = get_today_summary()
        assert report.by_payment.get("cash", 0) >= 10.0
        assert report.by_payment.get("card", 0) >= 20.0
        assert report.by_payment.get("pix", 0) >= 15.0

    def test_top_products(self):
        _make_sale(5.0, qty=3.0)
        report = get_today_summary()
        assert len(report.top_products) >= 1

    def test_daily_summaries_cover_range(self):
        d_from = date(2025, 1, 1)
        d_to = date(2025, 1, 7)
        report = get_report(d_from, d_to)
        assert len(report.daily_summaries) == 7
