import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class BusinessType(str, enum.Enum):
    retail = "retail"
    pharmacy = "pharmacy"
    clinic = "clinic"
    hotel = "hotel"


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    business_type: Mapped[BusinessType] = mapped_column(
        Enum(BusinessType, name="business_type_enum"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users = relationship("User", back_populates="business", lazy="selectin")
    products = relationship("Product", back_populates="business", lazy="selectin")
    stock_movements = relationship("StockMovement", back_populates="business", lazy="selectin")
    customers = relationship("Customer", back_populates="business", lazy="selectin")
    orders = relationship("Order", back_populates="business", lazy="selectin")
