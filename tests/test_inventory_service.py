"""Tests for inventory service."""
import os
import tempfile
import pytest

_tmpdir = tempfile.mkdtemp()
os.environ.setdefault("LOJAFLOW_DATA", _tmpdir)

from app.database import init_db
from app.services.inventory_service import adjust_stock, list_movements, set_stock
from app.services.product_service import create_product, get_product_by_id


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


def _make_product(**kwargs):
    defaults = {"name": "Produto Estoque", "sale_price": 5.0, "stock_qty": 10.0, "min_stock": 2.0}
    defaults.update(kwargs)
    return create_product(defaults)


class TestAdjustStock:
    def test_add_stock(self):
        p = _make_product(stock_qty=10.0)
        m = adjust_stock(p.id, 5.0, "Compra")
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 15.0
        assert m.movement_type == "in"
        assert m.qty_change == 5.0

    def test_remove_stock(self):
        p = _make_product(stock_qty=10.0)
        m = adjust_stock(p.id, -3.0, "Perda")
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 7.0
        assert m.movement_type == "out"

    def test_stock_never_goes_negative(self):
        p = _make_product(stock_qty=2.0)
        adjust_stock(p.id, -10.0, "Retirada excessiva")
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 0.0

    def test_product_not_found_raises(self):
        with pytest.raises(ValueError, match="não encontrado"):
            adjust_stock(99999, 1.0, "Produto inexistente")

    def test_zero_change_is_adjustment(self):
        p = _make_product(stock_qty=5.0)
        m = adjust_stock(p.id, 0.0, "Ajuste zero")
        assert m.movement_type == "adjustment"


class TestSetStock:
    def test_set_absolute(self):
        p = _make_product(stock_qty=10.0)
        m = set_stock(p.id, 25.0, "Inventário")
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 25.0
        assert m.movement_type == "adjustment"
        assert m.qty_before == 10.0
        assert m.qty_after == 25.0
        assert m.qty_change == 15.0

    def test_set_to_zero(self):
        p = _make_product(stock_qty=5.0)
        set_stock(p.id, 0.0, "Zeramento")
        updated = get_product_by_id(p.id)
        assert updated.stock_qty == 0.0

    def test_product_not_found_raises(self):
        with pytest.raises(ValueError):
            set_stock(99999, 10.0)


class TestListMovements:
    def test_list_all_movements(self):
        p = _make_product(name="Produto Mov")
        adjust_stock(p.id, 5.0, "Entrada")
        adjust_stock(p.id, -2.0, "Saída")
        movements = list_movements()
        assert len(movements) >= 2

    def test_filter_by_product(self):
        p1 = _make_product(name="Produto A")
        p2 = _make_product(name="Produto B")
        adjust_stock(p1.id, 1.0, "Mov P1")
        adjust_stock(p2.id, 2.0, "Mov P2")
        movs_p1 = list_movements(product_id=p1.id)
        assert all(m.product_id == p1.id for m in movs_p1)

    def test_product_eagerly_loaded(self):
        """Verifica que movement.product não causa DetachedInstanceError."""
        p = _make_product(name="Produto Eager")
        adjust_stock(p.id, 3.0, "Teste eager")
        movements = list_movements(product_id=p.id)
        assert len(movements) >= 1
        # This would raise DetachedInstanceError before the fix
        assert movements[0].product is not None
        assert movements[0].product.name == "Produto Eager"

    def test_limit_respected(self):
        p = _make_product(name="Produto Limite")
        for i in range(10):
            adjust_stock(p.id, 1.0, f"Mov {i}")
        movements = list_movements(limit=5)
        assert len(movements) <= 5
