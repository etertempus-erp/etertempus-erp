from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.resources.entities import UnitType


class PurchaseLineCreate(BaseModel):
    resource_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: UnitType
    unit_price: Decimal = Field(ge=0)


class PurchaseCreate(BaseModel):
    organization_id: UUID
    purchase_date: date
    supplier_name: str = Field(min_length=2, max_length=180)
    receipt_number: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    lines: list[PurchaseLineCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_lines(self):
        if not self.lines:
            raise ValueError("Agrega al menos un recurso a la compra.")
        return self


class PurchaseCancel(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class PurchaseLineRead(BaseModel):
    id: UUID
    resource_id: UUID
    resource_name: str
    quantity: Decimal
    unit: UnitType
    unit_price: Decimal
    line_total: Decimal


class PurchaseMovementRead(BaseModel):
    id: UUID
    resource_id: UUID
    resource_name: str
    type: str
    quantity: Decimal
    unit_cost_snapshot: Decimal | None = None
    occurred_at: datetime


class PurchaseRead(BaseModel):
    id: UUID
    code: str
    purchase_date: date
    supplier_name: str
    receipt_number: str | None = None
    status: str
    subtotal: Decimal
    total: Decimal
    notes: str | None = None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    lines: list[PurchaseLineRead] = []
    movements: list[PurchaseMovementRead] = []


class SupplierRead(BaseModel):
    id: UUID
    name: str


class PurchaseOptions(BaseModel):
    suppliers: list[SupplierRead]
