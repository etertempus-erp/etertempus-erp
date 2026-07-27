from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func, select
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.formulas.entities import FormulaStatus
from app.domain.production.entities import BatchStatus, MovementType
from app.domain.resources.entities import ResourceType, UnitType


def enum_values(enum_cls):
    return [member.value for member in enum_cls]


class Base(DeclarativeBase):
    pass


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(default=True)


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, values_callable=enum_values, name="user_role"),
        nullable=False,
        default=UserRole.OPERATOR,
    )
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSessionModel(Base):
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResourceModel(Base):
    __tablename__ = "resources"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[ResourceType] = mapped_column(
        SAEnum(ResourceType, values_callable=enum_values, name="resource_type"),
        nullable=False,
    )
    unit: Mapped[UnitType] = mapped_column(
        SAEnum(UnitType, values_callable=enum_values, name="unit_type"),
        nullable=False,
    )
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=Decimal("0"))
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ResourceCostModel(Base):
    __tablename__ = "resource_costs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    purchase_id: Mapped[UUID | None] = mapped_column(ForeignKey("purchases.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[UnitType] = mapped_column(
        SAEnum(UnitType, values_callable=enum_values, name="unit_type"),
        nullable=False,
    )
    supplier_name: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductPriceModel(Base):
    __tablename__ = "product_prices"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    product_resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    price_list_name: Mapped[str] = mapped_column(Text, nullable=False, default="Publico")
    sale_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    variable_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    contribution_margin: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    contribution_margin_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    effective_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FormulaModel(Base):
    __tablename__ = "formulas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    product_resource_id: Mapped[UUID | None] = mapped_column(ForeignKey("resources.id"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[FormulaStatus] = mapped_column(
        SAEnum(FormulaStatus, values_callable=enum_values, name="formula_status"),
        nullable=False,
        default=FormulaStatus.DRAFT,
    )
    active_version: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["FormulaItemModel"]] = relationship(
        back_populates="formula",
        cascade="all, delete-orphan",
        order_by="FormulaItemModel.sort_order",
    )


class FormulaItemModel(Base):
    __tablename__ = "formula_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    formula_id: Mapped[UUID] = mapped_column(ForeignKey("formulas.id", ondelete="CASCADE"), nullable=False)
    ingredient_resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    percentage: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    formula: Mapped[FormulaModel] = relationship(back_populates="items")


class ProductionBatchModel(Base):
    __tablename__ = "production_batches"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(40), nullable=False)
    elaboration_date: Mapped[date] = mapped_column(Date, nullable=False)
    product_resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    formula_id: Mapped[UUID] = mapped_column(ForeignKey("formulas.id"), nullable=False)
    mix_resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[UnitType] = mapped_column(
        SAEnum(UnitType, values_callable=enum_values, name="unit_type"),
        nullable=False,
        default=UnitType.G,
    )
    status: Mapped[BatchStatus] = mapped_column(
        SAEnum(BatchStatus, values_callable=enum_values, name="batch_status"),
        nullable=False,
        default=BatchStatus.ELABORATED,
    )
    ingredient_cost_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryMovementModel(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    production_batch_id: Mapped[UUID | None] = mapped_column(ForeignKey("production_batches.id"))
    purchase_id: Mapped[UUID | None] = mapped_column(ForeignKey("purchases.id"))
    type: Mapped[MovementType] = mapped_column(
        SAEnum(MovementType, values_callable=enum_values, name="movement_type"),
        nullable=False,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[UnitType] = mapped_column(
        SAEnum(UnitType, values_callable=enum_values, name="unit_type"),
        nullable=False,
    )
    unit_cost_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


def current_stock_query(resource_id: UUID):
    return select(func.coalesce(func.sum(InventoryMovementModel.quantity), 0)).where(
        InventoryMovementModel.resource_id == resource_id
    )


class SaleStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class SalesChannelModel(Base):
    __tablename__ = "sales_channels"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentMethodModel(Base):
    __tablename__ = "payment_methods"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpenseCategoryModel(Base):
    __tablename__ = "expense_categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PointOfSaleModel(Base):
    __tablename__ = "points_of_sale"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SaleModel(Base):
    __tablename__ = "sales"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    channel_id: Mapped[UUID] = mapped_column(ForeignKey("sales_channels.id"), nullable=False)
    point_of_sale_id: Mapped[UUID | None] = mapped_column(ForeignKey("points_of_sale.id"))
    customer_name: Mapped[str | None] = mapped_column(Text)
    payment_method_id: Mapped[UUID] = mapped_column(ForeignKey("payment_methods.id"), nullable=False)
    status: Mapped[SaleStatus] = mapped_column(
        SAEnum(SaleStatus, values_callable=enum_values, name="sale_status"),
        nullable=False,
        default=SaleStatus.CONFIRMED,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    created_by: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    details: Mapped[list["SaleDetailModel"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
    )


class SaleDetailModel(Base):
    __tablename__ = "sale_details"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    sale_id: Mapped[UUID] = mapped_column(ForeignKey("sales.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=Decimal("0"))
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sale: Mapped[SaleModel] = relationship(back_populates="details")


class SaleInventoryMovementModel(Base):
    __tablename__ = "sale_inventory_movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sale_detail_id: Mapped[UUID] = mapped_column(ForeignKey("sale_details.id", ondelete="CASCADE"), nullable=False)
    inventory_movement_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_movements.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportedSaleModel(Base):
    __tablename__ = "imported_sales"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_name: Mapped[str | None] = mapped_column(Text)
    department: Mapped[str | None] = mapped_column(Text)
    channel_name: Mapped[str | None] = mapped_column(Text)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    payment_method: Mapped[str | None] = mapped_column(Text)
    source_sheet: Mapped[str] = mapped_column(Text, nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    control_status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExpenseModel(Base):
    __tablename__ = "expenses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("expense_categories.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method_id: Mapped[UUID] = mapped_column(ForeignKey("payment_methods.id"), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    receipt_number: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="confirmed")
    origin: Mapped[str] = mapped_column(Text, nullable=False, default="system")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    cashbox_entry_id: Mapped[UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportedExpenseModel(Base):
    __tablename__ = "imported_expenses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category_name: Mapped[str] = mapped_column(Text, nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(Text)
    source_sheet: Mapped[str] = mapped_column(Text, nullable=False)
    source_row: Mapped[int] = mapped_column(nullable=False)
    control_status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PurchaseStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PurchaseModel(Base):
    __tablename__ = "purchases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"))
    supplier_name: Mapped[str] = mapped_column(Text, nullable=False)
    receipt_number: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PurchaseStatus] = mapped_column(
        SAEnum(PurchaseStatus, values_callable=enum_values, name="purchase_status"),
        nullable=False,
        default=PurchaseStatus.DRAFT,
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    details: Mapped[list["PurchaseDetailModel"]] = relationship(
        back_populates="purchase",
        cascade="all, delete-orphan",
    )


class PurchaseDetailModel(Base):
    __tablename__ = "purchase_details"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    purchase_id: Mapped[UUID] = mapped_column(ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(ForeignKey("resources.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    unit: Mapped[UnitType] = mapped_column(
        SAEnum(UnitType, values_callable=enum_values, name="unit_type"),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    purchase: Mapped[PurchaseModel] = relationship(back_populates="details")


class SupplierModel(Base):
    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
