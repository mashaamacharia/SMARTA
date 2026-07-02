import enum
import uuid
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class TaxCategory(str, enum.Enum):
    vat_16 = "vat_16"
    exempt = "exempt"
    zero_rated = "zero_rated"


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=5)
    units: Mapped[str] = mapped_column(String(50), default="pcs")
    # populated but unused until Project 11 (KRA module)
    tax_category: Mapped[TaxCategory | None] = mapped_column(
        Enum(TaxCategory, name="tax_category_enum"), nullable=True, default=TaxCategory.exempt
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("business_id", "sku", name="uq_business_sku"),
        CheckConstraint("quantity >= 0", name="ck_product_quantity_non_negative"),
    )

    business = relationship("Business", back_populates="products")
