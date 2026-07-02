from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class OrderItemCreate(BaseModel):
    product_id: str
    quantity: int


class OrderCreate(BaseModel):
    customer_id: Optional[str] = None
    channel: str
    notes: Optional[str] = None
    items: list[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: str


class OrderItemOut(BaseModel):
    id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: str
    business_id: str
    customer_id: Optional[str]
    status: str
    channel: str
    total_amount: Decimal
    vat_amount: Decimal
    notes: Optional[str]
    created_by: str
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True


class OrderList(BaseModel):
    items: list[OrderOut]
    total: int
    limit: int
    offset: int
