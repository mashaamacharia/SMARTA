import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache_keys import CacheKeys
from app.models.customer import Customer
from app.models.order import Order, OrderChannel, OrderStatus
from app.models.order_item import OrderItem
from app.models.product import Product
from app.models.stock_movement import MovementType, StockMovement
from app.models.user import User
from app.services.cache_service import CacheService


class InsufficientStockError(HTTPException):
    def __init__(self, product_id: uuid.UUID, available: int, requested: int):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "insufficient_stock",
                "product_id": str(product_id),
                "available": available,
                "requested": requested,
            },
        )


class OrderService:
    def __init__(
        self,
        db: AsyncSession,
        business_id: uuid.UUID,
        user_id: uuid.UUID,
        cache: CacheService | None = None,
    ):
        self.db = db
        self.business_id = business_id
        self.user_id = user_id
        self.cache = cache

    async def list_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        customer_id: Optional[uuid.UUID] = None,
    ) -> dict:
        query = select(Order).where(Order.business_id == self.business_id)

        if status_filter:
            query = query.where(Order.status == OrderStatus(status_filter))
        if date_from:
            query = query.where(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        if date_to:
            query = query.where(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        if customer_id:
            query = query.where(Order.customer_id == customer_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(Order.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        orders = result.scalars().all()

        return {"items": orders, "total": total, "limit": limit, "offset": offset}

    async def get_order(self, order_id: uuid.UUID) -> Order:
        result = await self.db.execute(
            select(Order).where(
                Order.id == order_id,
                Order.business_id == self.business_id,
            )
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order

    async def create_order(
        self, customer_id: Optional[uuid.UUID], channel: str, notes: Optional[str], items_data: list[dict]
    ) -> Order:
        if customer_id:
            cust_result = await self.db.execute(
                select(Customer).where(
                    Customer.id == customer_id,
                    Customer.business_id == self.business_id,
                )
            )
            if not cust_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Customer not found")

        order = Order(
            business_id=self.business_id,
            customer_id=customer_id,
            channel=OrderChannel(channel),
            notes=notes,
            created_by=self.user_id,
        )
        self.db.add(order)
        await self.db.flush()

        total_amount = Decimal("0.00")
        vat_amount = Decimal("0.00")

        for item_data in items_data:
            product_result = await self.db.execute(
                select(Product).where(
                    Product.id == uuid.UUID(item_data["product_id"]),
                    Product.business_id == self.business_id,
                    Product.is_active == True,
                )
            )
            product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item_data['product_id']} not found",
                )

            quantity = item_data["quantity"]
            unit_price = product.unit_price
            subtotal = unit_price * quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
            )
            self.db.add(order_item)

            total_amount += subtotal
            # vat_amount always 0.00 in Project 1 — computation lands in Project 11

        order.total_amount = total_amount
        order.vat_amount = Decimal("0.00")

        await self.db.flush()
        await self.db.commit()
        return order

    async def update_status(self, order_id: uuid.UUID, new_status: str) -> Order:
        order = await self.get_order(order_id)
        target_status = OrderStatus(new_status)

        if order.status == OrderStatus.cancelled:
            raise HTTPException(
                status_code=400,
                detail="Cannot update a cancelled order",
            )

        if order.status == OrderStatus.fulfilled:
            raise HTTPException(
                status_code=400,
                detail="Cannot update a fulfilled order",
            )

        if target_status == OrderStatus.confirmed and order.status == OrderStatus.pending:
            order = await self.confirm_order(order)

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

        await self.db.flush()
        await self.db.commit()

        if target_status == OrderStatus.confirmed and self.cache is not None:
            period = datetime.now().strftime("%Y-%m")
            await self.cache.invalidate_pattern(
                CacheKeys.product_pattern(str(self.business_id))
            )
            await self.cache.delete(
                CacheKeys.sales_report(str(self.business_id), period)
            )

        return order

    async def confirm_order(self, order: Order) -> Order:
        result = await self.db.execute(
            select(Order).where(Order.id == order.id).with_for_update()
        )
        order = result.scalar_one()

        for item in order.items:
            product_result = await self.db.execute(
                select(Product).where(Product.id == item.product_id).with_for_update()
            )
            product = product_result.scalar_one()

            if product.quantity < item.quantity:
                raise InsufficientStockError(
                    product_id=product.id,
                    available=product.quantity,
                    requested=item.quantity,
                )

            quantity_before = product.quantity
            product.quantity -= item.quantity

            movement = StockMovement(
                business_id=self.business_id,
                product_id=product.id,
                movement_type=MovementType.sale,
                quantity_change=-item.quantity,
                quantity_before=quantity_before,
                quantity_after=product.quantity,
                created_by=self.user_id,
            )
            self.db.add(movement)

        order.status = OrderStatus.confirmed
        return order
