"""Product and Category business logic."""
from __future__ import annotations

from sqlalchemy.orm import joinedload

from app.database import get_session
from app.models.product import Category, Product


# ── Category ──────────────────────────────────────────────────────────────────

def list_categories() -> list[Category]:
    with get_session() as s:
        return s.query(Category).order_by(Category.name).all()


def get_or_create_category(name: str) -> Category:
    with get_session() as s:
        cat = s.query(Category).filter_by(name=name).first()
        if not cat:
            cat = Category(name=name)
            s.add(cat)
            s.flush()
        return cat


# ── Product ───────────────────────────────────────────────────────────────────

def list_products(search: str = "", active_only: bool = True) -> list[Product]:
    with get_session() as s:
        q = s.query(Product).options(joinedload(Product.category))
        if active_only:
            q = q.filter(Product.active == True)  # noqa: E712
        if search:
            like = f"%{search}%"
            q = q.filter(
                Product.name.ilike(like) | Product.barcode.ilike(like)
            )
        return q.order_by(Product.name).all()


def get_product_by_id(product_id: int) -> Product | None:
    with get_session() as s:
        return s.get(Product, product_id)


def get_product_by_barcode(barcode: str) -> Product | None:
    with get_session() as s:
        return s.query(Product).filter_by(barcode=barcode, active=True).first()


def create_product(data: dict) -> Product:
    with get_session() as s:
        product = Product(**data)
        s.add(product)
        s.flush()
        s.refresh(product)
        return product


def update_product(product_id: int, data: dict) -> Product | None:
    with get_session() as s:
        product = s.get(Product, product_id)
        if not product:
            return None
        for key, value in data.items():
            setattr(product, key, value)
        s.flush()
        s.refresh(product)
        return product


def delete_product(product_id: int) -> bool:
    """Soft-delete: set active=False."""
    with get_session() as s:
        product = s.get(Product, product_id)
        if not product:
            return False
        product.active = False
        return True


def get_low_stock_products() -> list[Product]:
    with get_session() as s:
        return (
            s.query(Product)
            .filter(Product.active == True, Product.stock_qty <= Product.min_stock)  # noqa: E712
            .order_by(Product.stock_qty)
            .all()
        )
