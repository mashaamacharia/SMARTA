import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_business, get_current_user, get_db
from app.models.user import User
from app.schemas.order import (
    OrderCreate,
    OrderList,
    OrderOut,
    OrderStatusUpdate,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=OrderList)
async def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    customer_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = OrderService(db, business_id, user.id)
    return await service.list_orders(
        limit=limit,
        offset=offset,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id,
    )


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(
    body: OrderCreate,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = OrderService(db, business_id, user.id)
    customer_id = uuid.UUID(body.customer_id) if body.customer_id else None
    return await service.create_order(
        customer_id=customer_id,
        channel=body.channel,
        notes=body.notes,
        items_data=[i.model_dump() for i in body.items],
    )


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = OrderService(db, business_id, user.id)
    return await service.get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: uuid.UUID,
    body: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = OrderService(db, business_id, user.id)
    return await service.update_status(order_id, body.status)
