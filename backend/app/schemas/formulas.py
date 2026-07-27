from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.formulas.entities import FormulaStatus


class FormulaItemCreate(BaseModel):
    ingredient_resource_id: UUID
    percentage: Decimal = Field(gt=0, le=100, decimal_places=2)
    sort_order: int = 0


class FormulaCreate(BaseModel):
    organization_id: UUID
    name: str = Field(min_length=2, max_length=160)
    version: int = Field(ge=1)
    product_resource_id: UUID | None = None
    status: FormulaStatus = FormulaStatus.DRAFT
    active_version: bool = False
    notes: str | None = None
    items: list[FormulaItemCreate]


class FormulaRead(FormulaCreate):
    id: UUID


class FormulaItemRead(BaseModel):
    ingredient_resource_id: UUID
    ingredient_name: str
    percentage: Decimal
    sort_order: int


class FormulaDetail(BaseModel):
    id: UUID
    organization_id: UUID
    product_resource_id: UUID | None
    name: str
    version: int
    status: FormulaStatus
    active_version: bool
    notes: str | None = None
    items: list[FormulaItemRead]


class FormulaSummary(BaseModel):
    id: UUID
    organization_id: UUID
    product_resource_id: UUID | None
    name: str
    version: int
    status: FormulaStatus
    active_version: bool


class FormulaScaleRequest(BaseModel):
    target_weight: Decimal = Field(gt=0)
