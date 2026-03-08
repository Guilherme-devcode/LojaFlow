"""Tests for product service."""
import os
import tempfile
import pytest

# Point DB to a temp file for tests
_tmpdir = tempfile.mkdtemp()
os.environ["LOJAFLOW_DATA"] = _tmpdir

from app.database import init_db
from app.services.product_service import (
    create_product,
    delete_product,
    get_product_by_barcode,
    get_product_by_id,
    get_low_stock_products,
    list_products,
    update_product,
)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _make_product(**kwargs):
    defaults = {
        "name": "Produto Teste",
        "sale_price": 5.99,
        "stock_qty": 20.0,
        "min_stock": 5.0,
    }
    defaults.update(kwargs)
    return create_product(defaults)


class TestCreateProduct:
    def test_create_basic(self):
        p = _make_product(name="Arroz 1kg", sale_price=4.50)
        assert p.id is not None
        assert p.name == "Arroz 1kg"
        assert p.sale_price == 4.50
        assert p.active is True

    def test_create_with_barcode(self):
        p = _make_product(barcode="7891000315507")
        found = get_product_by_barcode("7891000315507")
        assert found is not None
        assert found.id == p.id

    def test_barcode_not_found(self):
        result = get_product_by_barcode("0000000000000")
        assert result is None


class TestListProducts:
    def test_list_all(self):
        _make_product(name="Feijão")
        _make_product(name="Macarrão")
        products = list_products()
        names = [p.name for p in products]
        assert "Feijão" in names
        assert "Macarrão" in names

    def test_search_by_name(self):
        _make_product(name="Biscoito Cream Cracker")
        _make_product(name="Refrigerante Cola")
        results = list_products(search="Biscoito")
        assert any("Biscoito" in p.name for p in results)
        assert not any("Refrigerante" in p.name for p in results)


class TestUpdateProduct:
    def test_update_price(self):
        p = _make_product(name="Produto X", sale_price=10.0)
        updated = update_product(p.id, {"sale_price": 12.50})
        assert updated.sale_price == 12.50

    def test_update_nonexistent(self):
        result = update_product(99999, {"name": "Ghost"})
        assert result is None


class TestDeleteProduct:
    def test_soft_delete(self):
        p = _make_product(name="Para Excluir")
        delete_product(p.id)
        found = get_product_by_id(p.id)
        # Should still exist but inactive
        assert found is not None
        assert found.active is False

    def test_not_in_active_list(self):
        p = _make_product(name="Deletado")
        delete_product(p.id)
        products = list_products(active_only=True)
        assert not any(x.id == p.id for x in products)


class TestLowStock:
    def test_low_stock_detected(self):
        _make_product(name="Produto Baixo", stock_qty=2.0, min_stock=5.0)
        low = get_low_stock_products()
        assert any(p.name == "Produto Baixo" for p in low)

    def test_ok_stock_not_flagged(self):
        _make_product(name="Produto OK", stock_qty=50.0, min_stock=5.0)
        low = get_low_stock_products()
        assert not any(p.name == "Produto OK" for p in low)
