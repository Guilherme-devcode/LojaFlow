"""Sales reporting and aggregation logic."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func

from app.database import get_session
from app.models.sale import Sale, SaleItem


@dataclass
class DailySummary:
    date: date
    total: float
    num_sales: int


@dataclass
class ProductSummary:
    product_name: str
    qty_sold: float
    revenue: float


@dataclass
class ReportData:
    date_from: date
    date_to: date
    total_revenue: float
    num_sales: int
    avg_ticket: float
    daily_summaries: list[DailySummary]
    top_products: list[ProductSummary]
    by_payment: dict[str, float]


def get_report(date_from: date, date_to: date) -> ReportData:
    dt_from = datetime.combine(date_from, datetime.min.time())
    dt_to = datetime.combine(date_to, datetime.max.time())

    with get_session() as s:
        sales = (
            s.query(Sale)
            .filter(Sale.status == "completed", Sale.created_at.between(dt_from, dt_to))
            .all()
        )

        total_revenue = sum(sale.total for sale in sales)
        num_sales = len(sales)
        avg_ticket = round(total_revenue / num_sales, 2) if num_sales else 0.0

        # Daily breakdown
        daily: dict[date, DailySummary] = {}
        current = date_from
        while current <= date_to:
            daily[current] = DailySummary(date=current, total=0.0, num_sales=0)
            current += timedelta(days=1)

        for sale in sales:
            d = sale.created_at.date()
            if d in daily:
                daily[d].total = round(daily[d].total + sale.total, 2)
                daily[d].num_sales += 1

        # Top products
        top_rows = (
            s.query(
                SaleItem.product_name,
                func.sum(SaleItem.qty).label("qty"),
                func.sum(SaleItem.subtotal).label("revenue"),
            )
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(Sale.status == "completed", Sale.created_at.between(dt_from, dt_to))
            .group_by(SaleItem.product_name)
            .order_by(func.sum(SaleItem.subtotal).desc())
            .limit(10)
            .all()
        )
        top_products = [
            ProductSummary(product_name=r.product_name, qty_sold=r.qty, revenue=round(r.revenue, 2))
            for r in top_rows
        ]

        # Payment breakdown
        by_payment: dict[str, float] = {}
        for sale in sales:
            method = sale.payment_method
            by_payment[method] = round(by_payment.get(method, 0.0) + sale.total, 2)

        return ReportData(
            date_from=date_from,
            date_to=date_to,
            total_revenue=round(total_revenue, 2),
            num_sales=num_sales,
            avg_ticket=avg_ticket,
            daily_summaries=list(daily.values()),
            top_products=top_products,
            by_payment=by_payment,
        )


def get_today_summary() -> ReportData:
    today = date.today()
    return get_report(today, today)


def export_csv(date_from: date, date_to: date, filepath) -> int:
    """Export sale items for the period to a CSV file. Returns row count."""
    import csv
    from pathlib import Path

    dt_from = datetime.combine(date_from, datetime.min.time())
    dt_to = datetime.combine(date_to, datetime.max.time())

    with get_session() as s:
        rows = (
            s.query(SaleItem, Sale)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(Sale.status == "completed", Sale.created_at.between(dt_from, dt_to))
            .order_by(Sale.created_at)
            .all()
        )

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Data", "Venda #", "Produto", "Qtd.", "Preço Unit. (R$)",
            "Subtotal (R$)", "Pagamento"
        ])
        for item, sale in rows:
            writer.writerow([
                sale.created_at.strftime("%d/%m/%Y %H:%M"),
                sale.id,
                item.product_name,
                f"{item.qty:.3f}".replace(".", ","),
                f"{item.unit_price:.2f}".replace(".", ","),
                f"{item.subtotal:.2f}".replace(".", ","),
                sale.payment_method,
            ])

    return len(rows)
