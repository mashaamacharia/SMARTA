from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str
    sku: str
    category: Optional[str] = None
    unit_price: Decimal = Field(max_digits=12, decimal_places=2)
    cost_price: Decimal = Field(max_digits=12, decimal_places=2)
    quantity: int = 0
    low_stock_threshold: int = 5
    units: str = "pcs"
    tax_category: str = "exempt"


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    cost_price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2)
    low_stock_threshold: Optional[int] = None
    units: Optional[str] = None
    tax_category: Optional[str] = None


class StockAdjustRequest(BaseModel):
    quantity_change: int
    reason: str = "adjustment"
    note: Optional[str] = None


class ProductOut(BaseModel):
    id: str
    business_id: str
    name: str
    sku: str
    category: Optional[str]
    unit_price: Decimal
    cost_price: Decimal
    quantity: int
    low_stock_threshold: int
    units: str
    tax_category: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class ProductList(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int
