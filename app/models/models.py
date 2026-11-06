from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.db import Base


class Category(Base):
    """Категории изделий."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    """Справочник изделий."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("length(sku) >= 3", name="check_product_sku_min_length"),
        Index("idx_products_sku", "sku"),
        Index("idx_products_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    category: Mapped["Category"] = relationship(back_populates="products")
    parameters_assoc: Mapped[list["ProductParameter"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )
    generation_logs: Mapped[list["GenerationLog"]] = relationship(back_populates="product")


class Parameter(Base):
    """Справочник параметров изделий."""

    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)

    product_parameters: Mapped[list["ProductParameter"]] = relationship(back_populates="parameter")


class ProductParameter(Base):
    """Ассоциативная таблица связи M:M (какие параметры есть у изделия и с каким значением)."""

    __tablename__ = "product_parameters"
    __table_args__ = (Index("idx_product_parameters_product", "product_id"),)

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        primary_key=True,
        nullable=False,
    )
    parameter_id: Mapped[int] = mapped_column(
        ForeignKey("parameters.id"),
        primary_key=True,
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(255), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="parameters_assoc")
    parameter: Mapped["Parameter"] = relationship(back_populates="product_parameters")


class Template(Base):
    """Шаблоны DOCX для генерации паспортов."""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    required_parameter_codes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    generation_logs: Mapped[list["GenerationLog"]] = relationship(back_populates="template")


class GenerationLog(Base):
    """История и аудит генераций паспортов."""

    __tablename__ = "generation_log"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failed')",
            name="check_generation_log_status",
        ),
        Index("idx_generation_log_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("templates.id"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    output_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    product: Mapped["Product"] = relationship(back_populates="generation_logs")
    template: Mapped["Template"] = relationship(back_populates="generation_logs")
