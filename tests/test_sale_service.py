"""Tests for sale service."""
import os
import tempfile
import pytest

_tmpdir = tempfile.mkdtemp()
os.environ["LOJAFLOW_DATA"] = _tmpdir

from app.database import init_db
from app.services.product_service import create_product, get_product_by_id
from app.services.sale_service import (
    Cart,
    CartItem,
    add_product_to_cart,
    finalize_sale,
    get_sale_by_id,
    list_sales,
)


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


class TestCancelSale:
    def test_cancel_restores_stock(self):
        from app.services.sale_service import cancel_sale
        p = _make_product(name="Item Cancelar", sale_price=8.0, stock_qty=10.0)
        cart = Cart()
        cart.add_or_increment(CartItem(
            product_id=p.id, product_name=p.name, unit_price=8.0, qty=4
        ))
        sale = finalize_sale(cart, payment_method="cash", amount_paid=32.0)
        assert get_product_by_id(p.id).stock_qty == 6.0

        cancel_sale(sale.id, "Teste de cancelamento")
        assert get_product_by_id(p.id).stock_qty == 10.0

    def test_cancel_changes_status(self):
        from app.services.sale_service import cancel_sale, get_sale_by_id
        p = _make_product(name="Item Status", sale_price=5.0, stock_qty=20.0)
        cart = Cart()
        cart.add_or_increment(CartItem(
            product_id=p.id, product_name=p.name, unit_price=5.0, qty=1
        ))
        sale = finalize_sale(cart, payment_method="card", amount_paid=5.0)
        cancel_sale(sale.id)
        updated = get_sale_by_id(sale.id)
        assert updated.status == "cancelled"

    def test_cancel_already_cancelled_raises(self):
        from app.services.sale_service import cancel_sale
        p = _make_product(name="Item Double Cancel", sale_price=5.0, stock_qty=20.0)
        cart = Cart()
        cart.add_or_increment(CartItem(
            product_id=p.id, product_name=p.name, unit_price=5.0, qty=1
        ))
        sale = finalize_sale(cart, payment_method="cash", amount_paid=5.0)
        cancel_sale(sale.id)
        with pytest.raises(ValueError):
            cancel_sale(sale.id)


class TestEagerLoading:
    def test_list_sales_items_accessible_after_session_close(self):
        """Verifica que sale.items não causa DetachedInstanceError."""
        p = _make_product(name="Produto Eager Sale", sale_price=10.0, stock_qty=10.0)
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=p.id, product_name=p.name, unit_price=10.0, qty=2))
        finalize_sale(cart, payment_method="cash", amount_paid=20.0)

        sales = list_sales()
        assert len(sales) >= 1
        # This would raise DetachedInstanceError before the fix
        assert len(sales[0].items) >= 1
        assert sales[0].items[0].product_name == "Produto Eager Sale"

    def test_get_sale_by_id_items_accessible(self):
        """Verifica que get_sale_by_id carrega items eagerly."""
        p = _make_product(name="Item Detalhe", sale_price=8.0, stock_qty=5.0)
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=p.id, product_name=p.name, unit_price=8.0, qty=1))
        created = finalize_sale(cart, payment_method="pix", amount_paid=8.0)

        sale = get_sale_by_id(created.id)
        assert sale is not None
        # This would raise DetachedInstanceError before the fix
        assert len(sale.items) == 1
        assert sale.items[0].qty == 1.0

    def test_get_sale_by_id_not_found_returns_none(self):
        result = get_sale_by_id(99999)
        assert result is None

    def test_list_sales_item_count_matches(self):
        """Qtd de itens na venda deve bater com o que foi adicionado."""
        p1 = _make_product(name="P1 Multi", sale_price=5.0, stock_qty=10.0)
        p2 = _make_product(name="P2 Multi", sale_price=3.0, stock_qty=10.0)
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=p1.id, product_name=p1.name, unit_price=5.0, qty=1))
        cart.add_or_increment(CartItem(product_id=p2.id, product_name=p2.name, unit_price=3.0, qty=2))
        sale = finalize_sale(cart, payment_method="card", amount_paid=11.0)

        sales = list_sales()
        found = next((s for s in sales if s.id == sale.id), None)
        assert found is not None
        assert len(found.items) == 2


class TestCartEdgeCases:
    def test_clear_resets_discount(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=10.0))
        cart.discount = 5.0
        cart.clear()
        assert cart.discount == 0.0
        assert len(cart.items) == 0

    def test_subtotal_multiple_items(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="A", unit_price=3.0, qty=2))
        cart.add_or_increment(CartItem(product_id=2, product_name="B", unit_price=5.0, qty=1))
        assert cart.subtotal == 11.0

    def test_discount_larger_than_subtotal_gives_zero_total(self):
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=1, product_name="X", unit_price=10.0))
        cart.discount = 999.0
        assert cart.total == 0.0

    def test_finalize_card_change_is_zero(self):
        p = _make_product(name="Item Cartão", sale_price=15.0, stock_qty=5.0)
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=p.id, product_name=p.name, unit_price=15.0, qty=1))
        sale = finalize_sale(cart, payment_method="card", amount_paid=15.0)
        assert sale.change_given == 0.0

    def test_finalize_pix_change_is_zero(self):
        p = _make_product(name="Item Pix", sale_price=20.0, stock_qty=5.0)
        cart = Cart()
        cart.add_or_increment(CartItem(product_id=p.id, product_name=p.name, unit_price=20.0, qty=1))
        sale = finalize_sale(cart, payment_method="pix", amount_paid=20.0)
        assert sale.change_given == 0.0
