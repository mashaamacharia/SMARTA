import uuid
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, TaxCategory
from app.models.stock_movement import MovementType, StockMovement


class ProductService:
    def __init__(self, db: AsyncSession, business_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.business_id = business_id
        self.user_id = user_id

    async def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None,
        category: Optional[str] = None,
        low_stock: Optional[bool] = None,
    ) -> dict:
        query = select(Product).where(
            Product.business_id == self.business_id,
            Product.is_active == True,
        )

        if search:
            query = query.where(Product.name.ilike(f"%{search}%"))
        if category:
            query = query.where(Product.category == category)
        if low_stock:
            query = query.where(Product.quantity <= Product.low_stock_threshold)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        query = query.order_by(Product.name).limit(limit).offset(offset)
        result = await self.db.execute(query)
        products = result.scalars().all()

        return {"items": products, "total": total, "limit": limit, "offset": offset}

    async def get_product(self, product_id: uuid.UUID) -> Product:
        result = await self.db.execute(
            select(Product).where(
                Product.id == product_id,
                Product.business_id == self.business_id,
            )
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product

    async def create_product(self, data: dict) -> Product:
        existing = await self.db.execute(
            select(Product).where(
                Product.business_id == self.business_id,
                Product.sku == data["sku"],
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with SKU '{data['sku']}' already exists",
            )

        product = Product(
            business_id=self.business_id,
            name=data["name"],
            sku=data["sku"],
            category=data.get("category"),
            unit_price=Decimal(str(data["unit_price"])),
            cost_price=Decimal(str(data["cost_price"])),
            quantity=data.get("quantity", 0),
            low_stock_threshold=data.get("low_stock_threshold", 5),
            units=data.get("units", "pcs"),
            tax_category=TaxCategory(data["tax_category"]) if data.get("tax_category") else None,
        )
        self.db.add(product)
        await self.db.flush()
        await self.db.commit()
        return product

    async def update_product(
        self, product_id: uuid.UUID, data: dict
    ) -> Product:
        product = await self.get_product(product_id)

        if "sku" in data and data["sku"] != product.sku:
            existing = await self.db.execute(
                select(Product).where(
                    Product.business_id == self.business_id,
                    Product.sku == data["sku"],
                    Product.id != product_id,
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"SKU '{data['sku']}' already in use",
                )

        for field in ("name", "sku", "category", "low_stock_threshold", "units"):
            if field in data:
                setattr(product, field, data[field])

        if "unit_price" in data:
            product.unit_price = Decimal(str(data["unit_price"]))
        if "cost_price" in data:
            product.cost_price = Decimal(str(data["cost_price"]))
        if "tax_category" in data:
            product.tax_category = TaxCategory(data["tax_category"])

        await self.db.flush()
        await self.db.commit()
        return product

    async def delete_product(self, product_id: uuid.UUID) -> None:
        product = await self.get_product(product_id)
        product.is_active = False
        await self.db.flush()
        await self.db.commit()

    async def adjust_stock(
        self, product_id: uuid.UUID, quantity_change: int, reason: str, note: Optional[str] = None
    ) -> Product:
        product = await self.get_product(product_id)
        new_quantity = product.quantity + quantity_change
        if new_quantity < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient stock. Available: {product.quantity}, requested change: {quantity_change}",
            )

        movement_type = MovementType.adjustment
        if reason == "restock":
            movement_type = MovementType.restock
        elif reason == "return":
            movement_type = MovementType.return_
        elif reason == "sale":
            movement_type = MovementType.sale

        quantity_before = product.quantity
        product.quantity = new_quantity

        movement = StockMovement(
            business_id=self.business_id,
            product_id=product.id,
            movement_type=movement_type,
            quantity_change=quantity_change,
            quantity_before=quantity_before,
            quantity_after=product.quantity,
            note=note,
            created_by=self.user_id,
        )
        self.db.add(movement)
        await self.db.flush()
        await self.db.commit()
        return product
