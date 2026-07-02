import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    fulfilled = "fulfilled"
    cancelled = "cancelled"


class OrderChannel(str, enum.Enum):
    walk_in = "walk_in"
    whatsapp = "whatsapp"
    storefront = "storefront"


class Order(TimestampMixin, Base):
    __tablename__ = "orders"

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id"), index=True, nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status_enum"), default=OrderStatus.pending
    )
    channel: Mapped[OrderChannel] = mapped_column(
        Enum(OrderChannel, name="order_channel_enum"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    # always 0.00 in Project 1 — real calculation lands in Project 11
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    business = relationship("Business", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy="selectin")
