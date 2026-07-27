from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.resources.entities import ResourceType, UnitType


class ResourceCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    type: ResourceType
    unit: UnitType
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)


class ResourceRead(ResourceCreate):
    id: UUID
    active: bool
    latest_unit_cost: Decimal | None = None
    latest_supplier_name: str | None = None


class ResourceUpdate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name: str = Field(min_length=2, max_length=160)
    type: ResourceType
    unit: UnitType
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)
    active: bool = True


class StockAdjustmentCreate(BaseModel):
    organization_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: UnitType
    reason: str = "Carga inicial de stock"


class StockSetCreate(BaseModel):
    organization_id: UUID
    quantity: Decimal = Field(ge=0)
    unit: UnitType
    reason: str = "Ajuste de stock actual"


class ResourceStockRead(BaseModel):
    resource_id: UUID
    code: str
    name: str
    type: ResourceType
    unit: UnitType
    quantity: Decimal
