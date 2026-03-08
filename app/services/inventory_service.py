"""Inventory / stock management business logic."""
from __future__ import annotations

from app.database import get_session
from app.models.product import Product
from app.models.sale import StockMovement


def adjust_stock(product_id: int, qty_change: float, reason: str = "") -> StockMovement:
    """Adjust stock by qty_change (positive = add, negative = remove)."""
    with get_session() as s:
        product: Product | None = s.get(Product, product_id)
        if not product:
            raise ValueError(f"Produto #{product_id} não encontrado")

        qty_before = product.stock_qty
        product.stock_qty = max(0.0, round(qty_before + qty_change, 3))
        movement_type = "in" if qty_change > 0 else ("adjustment" if qty_change == 0 else "out")

        movement = StockMovement(
            product_id=product_id,
            movement_type=movement_type,
            qty_before=qty_before,
            qty_change=qty_change,
            qty_after=product.stock_qty,
            reason=reason,
        )
        s.add(movement)
        s.flush()
        s.refresh(movement)
        return movement


def set_stock(product_id: int, new_qty: float, reason: str = "Ajuste manual") -> StockMovement:
    """Set absolute stock quantity."""
    with get_session() as s:
        product: Product | None = s.get(Product, product_id)
        if not product:
            raise ValueError(f"Produto #{product_id} não encontrado")

        qty_before = product.stock_qty
        qty_change = new_qty - qty_before
        product.stock_qty = new_qty

        movement = StockMovement(
            product_id=product_id,
            movement_type="adjustment",
            qty_before=qty_before,
            qty_change=qty_change,
            qty_after=new_qty,
            reason=reason,
        )
        s.add(movement)
        s.flush()
        s.refresh(movement)
        return movement


def list_movements(product_id: int | None = None, limit: int = 200) -> list[StockMovement]:
    with get_session() as s:
        q = s.query(StockMovement)
        if product_id:
            q = q.filter(StockMovement.product_id == product_id)
        return q.order_by(StockMovement.created_at.desc()).limit(limit).all()
