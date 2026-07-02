import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_business, get_current_user, get_db
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductList,
    ProductOut,
    ProductUpdate,
    StockAdjustRequest,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductList)
async def list_products(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    low_stock: Optional[bool] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    return await service.list_products(
        limit=limit, offset=offset, search=search, category=category, low_stock=low_stock
    )


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    return await service.create_product(body.model_dump())


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    return await service.get_product(product_id)


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: uuid.UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    return await service.update_product(
        product_id, {k: v for k, v in body.model_dump().items() if v is not None}
    )


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    await service.delete_product(product_id)


@router.post("/{product_id}/adjust", response_model=ProductOut)
async def adjust_stock(
    product_id: uuid.UUID,
    body: StockAdjustRequest,
    db: AsyncSession = Depends(get_db),
    business_id: uuid.UUID = Depends(get_current_business),
    user: User = Depends(get_current_user),
):
    service = ProductService(db, business_id, user.id)
    return await service.adjust_stock(
        product_id, body.quantity_change, body.reason, body.note
    )
