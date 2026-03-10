"""Sale and cart business logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.database import get_session
from app.models.product import Product
from app.models.sale import Sale, SaleItem, StockMovement


@dataclass
class CartItem:
    product_id: int
    product_name: str
    unit_price: float
    qty: float = 1.0
    unit: str = "un"

    @property
    def subtotal(self) -> float:
        return round(self.unit_price * self.qty, 2)


@dataclass
class Cart:
    items: list[CartItem] = field(default_factory=list)
    discount: float = 0.0

    @property
    def subtotal(self) -> float:
        return round(sum(i.subtotal for i in self.items), 2)

    @property
    def total(self) -> float:
        return max(0.0, round(self.subtotal - self.discount, 2))

    def add_or_increment(self, item: CartItem):
        for existing in self.items:
            if existing.product_id == item.product_id:
                existing.qty = round(existing.qty + item.qty, 3)
                return
        self.items.append(item)

    def remove(self, product_id: int):
        self.items = [i for i in self.items if i.product_id != product_id]

    def clear(self):
        self.items.clear()
        self.discount = 0.0


def add_product_to_cart(cart: Cart, barcode_or_id: str, qty: float = 1.0) -> CartItem | None:
    """Look up product by barcode/id and add it to the cart."""
    from app.services.product_service import get_product_by_barcode, get_product_by_id

    product = None
    if barcode_or_id.isdigit():
        product = get_product_by_barcode(barcode_or_id) or get_product_by_id(int(barcode_or_id))
    else:
        product = get_product_by_barcode(barcode_or_id)

    if not product:
        return None

    item = CartItem(
        product_id=product.id,
        product_name=product.name,
        unit_price=product.sale_price,
        qty=qty,
        unit=product.unit,
    )
    cart.add_or_increment(item)
    return item


def finalize_sale(
    cart: Cart,
    payment_method: str,
    amount_paid: float,
    customer_id: int | None = None,
    user_id: int | None = None,
) -> Sale:
    """Persist sale and deduct stock. Returns the created Sale."""
    if not cart.items:
        raise ValueError("Carrinho vazio")

    change = round(amount_paid - cart.total, 2) if payment_method == "cash" else 0.0

    with get_session() as s:
        sale = Sale(
            customer_id=customer_id,
            user_id=user_id,
            subtotal=cart.subtotal,
            discount=cart.discount,
            total=cart.total,
            payment_method=payment_method,
            amount_paid=amount_paid,
            change_given=change,
            status="completed",
            created_at=datetime.now(),
        )
        s.add(sale)
        s.flush()

        for cart_item in cart.items:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=cart_item.product_id,
                product_name=cart_item.product_name,
                unit_price=cart_item.unit_price,
                qty=cart_item.qty,
                subtotal=cart_item.subtotal,
            )
            s.add(sale_item)

            # Deduct stock
            product: Product | None = s.get(Product, cart_item.product_id)
            if product:
                qty_before = product.stock_qty
                product.stock_qty = max(0.0, round(qty_before - cart_item.qty, 3))
                movement = StockMovement(
                    product_id=product.id,
                    movement_type="out",
                    qty_before=qty_before,
                    qty_change=-cart_item.qty,
                    qty_after=product.stock_qty,
                    reason=f"Venda #{sale.id}",
                )
                s.add(movement)

        s.flush()
        s.refresh(sale)
        return sale


def get_sale_by_id(sale_id: int) -> Sale | None:
    with get_session() as s:
        return s.get(Sale, sale_id)


def list_sales(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_cancelled: bool = False,
    customer_id: int | None = None,
) -> list[Sale]:
    with get_session() as s:
        q = s.query(Sale)
        if not include_cancelled:
            q = q.filter(Sale.status == "completed")
        if date_from:
            q = q.filter(Sale.created_at >= date_from)
        if date_to:
            q = q.filter(Sale.created_at <= date_to)
        if customer_id is not None:
            q = q.filter(Sale.customer_id == customer_id)
        return q.order_by(Sale.created_at.desc()).all()


def cancel_sale(sale_id: int, reason: str = "") -> Sale:
    """Cancel a completed sale and restore stock for all items."""
    with get_session() as s:
        sale = s.get(Sale, sale_id)
        if not sale:
            raise ValueError(f"Venda #{sale_id} não encontrada")
        if sale.status != "completed":
            raise ValueError(f"Venda #{sale_id} já está {sale.status}")

        sale.status = "cancelled"

        for item in sale.items:
            if item.product_id is None:
                continue
            product = s.get(Product, item.product_id)
            if product:
                qty_before = product.stock_qty
                product.stock_qty = round(qty_before + item.qty, 3)
                movement = StockMovement(
                    product_id=product.id,
                    movement_type="in",
                    qty_before=qty_before,
                    qty_change=item.qty,
                    qty_after=product.stock_qty,
                    reason=f"Cancelamento venda #{sale_id}: {reason}",
                )
                s.add(movement)

        s.flush()
        s.refresh(sale)
        return sale
