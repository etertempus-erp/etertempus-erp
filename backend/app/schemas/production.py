from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ProductionBatchCreate(BaseModel):
    organization_id: UUID
    product_resource_id: UUID
    formula_id: UUID
    elaboration_date: date
    target_weight: Decimal = Field(gt=0)
    notes: str | None = None


class ProductionBatchPreview(BaseModel):
    formula_id: UUID
    target_weight: Decimal
    ingredient_grams: dict[str, Decimal]


class ProductionBatchRead(BaseModel):
    id: UUID
    batch_number: str
    mix_resource_id: UUID
    target_weight: Decimal


class ProductionBatchSummary(BaseModel):
    id: UUID
    batch_number: str
    product_resource_id: UUID
    formula_id: UUID
    mix_resource_id: UUID
    elaboration_date: date
    target_weight: Decimal
    status: str
