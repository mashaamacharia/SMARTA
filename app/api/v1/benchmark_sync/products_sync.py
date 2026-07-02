# BENCHMARK ONLY — not shipped to production
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement

router = APIRouter(prefix="/api/v1/benchmark-sync", tags=["benchmark-sync"])

sync_engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
SyncSession = sessionmaker(bind=sync_engine)


class StatusUpdate(BaseModel):
    status: str


@router.get("/products")
def list_products_sync(limit: int = 50, offset: int = 0):
    session: Session = SyncSession()
    try:
        result = session.execute(
            select(Product).where(Product.is_active == True).limit(limit).offset(offset)
        )
        products = result.scalars().all()
        return {"items": [str(p.id) for p in products], "count": len(products)}
    finally:
        session.close()


@router.patch("/orders/{order_id}/status")
def update_order_status_sync(order_id: uuid.UUID, body: StatusUpdate):
    session: Session = SyncSession()
    try:
        order = session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        ).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        target_status = OrderStatus(body.status)

        if target_status == OrderStatus.confirmed and order.status == OrderStatus.pending:
            for item in order.items:
                product = session.execute(
                    select(Product).where(Product.id == item.product_id).with_for_update()
                ).scalar_one()
                if product.quantity < item.quantity:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "error": "insufficient_stock",
                            "product_id": str(product.id),
                            "available": product.quantity,
                            "requested": item.quantity,
                        },
                    )
                quantity_before = product.quantity
                product.quantity -= item.quantity
                movement = StockMovement(
                    business_id=order.business_id,
                    product_id=product.id,
                    movement_type=MovementType.sale,
                    quantity_change=-item.quantity,
                    quantity_before=quantity_before,
                    quantity_after=product.quantity,
                    created_by=order.created_by,
                )
                session.add(movement)
            order.status = OrderStatus.confirmed

        elif target_status == OrderStatus.cancelled and order.status in (
            OrderStatus.pending, OrderStatus.confirmed
        ):
            order.status = OrderStatus.cancelled

        elif target_status == OrderStatus.fulfilled and order.status == OrderStatus.confirmed:
            order.status = OrderStatus.fulfilled

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot transition from {order.status.value} to {target_status.value}",
            )

        session.commit()
        return {"id": str(order.id), "status": order.status.value}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
