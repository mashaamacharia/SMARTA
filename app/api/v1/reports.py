import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache_keys import CacheKeys
from app.dependencies import get_current_business, get_current_user, get_db, get_redis
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.user import User
from app.schemas.report import SalesReportOut
from app.services.cache_service import CacheService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/sales", response_model=SalesReportOut)
async def sales_report(
    period: str = Query(default=None, description="YYYY-MM format"),
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
    redis: Redis | None = Depends(get_redis),
):
    from datetime import datetime

    period = period or datetime.now().strftime("%Y-%m")

    cache_service = CacheService(redis) if redis is not None else None
    if cache_service is not None:
        cache_key = CacheKeys.sales_report(str(business_id), period)
        cached = await cache_service.get(cache_key)
        if cached is not None:
            return cached

    year, month = period.split("-")
    month_start = f"{year}-{month}-01"

    result = await db.execute(
        select(
            func.count(Order.id.distinct()).label("total_orders"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("total_revenue"),
            func.coalesce(
                func.sum(OrderItem.subtotal - (Product.cost_price * OrderItem.quantity)), 0
            ).label("gross_profit"),
            func.count(func.distinct(Order.customer_id)).label("unique_customers"),
        )
        .select_from(Order)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(Product, OrderItem.product_id == Product.id)
        .where(
            Order.business_id == business_id,
            Order.status == OrderStatus.fulfilled,
            Order.created_at >= text(f"'{month_start}'::date"),
            Order.created_at < text(f"('{month_start}'::date + interval '1 month')"),
        )
    )
    row = result.one()

    data = SalesReportOut(
        total_orders=row.total_orders,
        total_revenue=row.total_revenue,
        gross_profit=row.gross_profit,
        unique_customers=row.unique_customers,
        period=period,
    )

    if cache_service is not None:
        await cache_service.set(cache_key, data.model_dump(), ttl=1800)

    return data
