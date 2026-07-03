from decimal import Decimal

from pydantic import BaseModel


class SalesReportOut(BaseModel):
    total_orders: int
    total_revenue: Decimal
    gross_profit: Decimal
    unique_customers: int
    period: str
