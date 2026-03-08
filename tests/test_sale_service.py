"""Tests for sale service."""
import os
import tempfile
import pytest

_tmpdir = tempfile.mkdtemp()
os.environ["LOJAFLOW_DATA"] = _tmpdir

from app.database import init_db
from app.services.product_service import create_product
from app.services.sale_service import Cart, CartItem, add_product_to_cart, finalize_sale


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _make_product(**kwargs):
    defaults = {"name": "Produto Teste", "sale_price": 5.99, "stock_qty": 20.0, "min_stock": 5.0}
    defaults.update(kwargs)
    return create_product(defaults)


class TestCart:
    def test_add_item(self):
        cart = Cart()
        item = CartItem(product_id=1, product_name="X", unit_price=10.0, qty=2)
        cart.add_or_increment(item)
        assert len(cart.items) == 1
        assert cart.subtotal == 20.0

    def test_increment_existing(self):
        cart = Cart()
        item = CartItem(product_id=1, product_name="X", unit_price=10.0, qty=1)
        cart.add_or_increment(item)
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=10.0, qty=2))
        assert len(cart.items) == 1
        assert cart.items[0].qty == 3.0

    def test_remove_item(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=5.0))
        cart.add_or_increment(CartItem(product_id=2, product_name="Y", unit_price=3.0))
        cart.remove(1)
        assert len(cart.items) == 1
        assert cart.items[0].product_id == 2

    def test_discount(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=10.0, qty=1))
        cart.discount = 2.0
        assert cart.total == 8.0

    def test_total_never_negative(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=5.0))
        cart.discount = 100.0
        assert cart.total == 0.0


class TestAddProductToCart:
    def test_add_by_barcode(self):
        p = _make_product(name="Coca-Cola", barcode="7894900011517", sale_price=6.0)
        cart = Cart()
        item = add_product_to_cart(cart, "7894900011517")
        assert item is not None
        assert item.product_id == p.id
        assert item.unit_price == 6.0

    def test_not_found(self):
        cart = Cart()
        item = add_product_to_cart(cart, "9999999999999")
        assert item is None


class TestFinalizeSale:
    def test_finalize_cash(self):
        p = _make_product(name="Item Venda", sale_price=10.0, stock_qty=5.0)
        cart = Cart()
        cart.add_or_increment(CartItem(
            product_id=p.id, product_name=p.name, unit_price=10.0, qty=2
        ))
        sale = finalize_sale(cart, payment_method="cash", amount_paid=25.0)
        assert sale.id is not None
        assert sale.total == 20.0
        assert sale.change_given == 5.0
        assert sale.status == "completed"

    def test_stock_deducted(self):
        from app.services.product_service import get_product_by_id
        p = _make_product(name="Item Stock", sale_price=5.0, stock_qty=10.0)
        cart = Cart()
        cart.add_or_increment(CartItem(
            product_id=p.id, product_name=p.name, unit_price=5.0, qty=3
        ))
        finalize_sale(cart, payment_method="pix", amount_paid=15.0)
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 7.0

    def test_empty_cart_raises(self):
        cart = Cart()
        with pytest.raises(ValueError, match="Carrinho vazio"):
            finalize_sale(cart, payment_method="cash", amount_paid=0.0)
