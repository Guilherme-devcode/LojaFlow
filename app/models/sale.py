"""Sale, SaleItem, and StockMovement models."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    total: Mapped[float] = mapped_column(Float, default=0.0)
    payment_method: Mapped[str] = mapped_column(String(20), default="cash")  # cash, card, pix
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    change_given: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="completed")  # completed, cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[list["SaleItem"]] = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="sales")

    def __repr__(self) -> str:
        return f"<Sale #{self.id} R${self.total:.2f}>"


class SaleItem(Base):
    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("products.id"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)  # snapshot
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)  # snapshot
    qty: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    sale: Mapped["Sale"] = relationship("Sale", back_populates="items")
    product: Mapped["Product | None"] = relationship("Product", back_populates="sale_items")

    def __repr__(self) -> str:
        return f"<SaleItem {self.product_name} x{self.qty}>"


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)  # in, out, adjustment
    qty_before: Mapped[float] = mapped_column(Float, nullable=False)
    qty_change: Mapped[float] = mapped_column(Float, nullable=False)
    qty_after: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    product: Mapped["Product"] = relationship("Product", back_populates="stock_movements")

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type} {self.qty_change}>"
