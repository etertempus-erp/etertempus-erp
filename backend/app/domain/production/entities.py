from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.resources.entities import UnitType


class BatchStatus(StrEnum):
    ELABORATED = "elaborated"
    PARTIALLY_PACKAGED = "partially_packaged"
    FULLY_PACKAGED = "fully_packaged"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class MovementType(StrEnum):
    PURCHASE = "purchase"
    PURCHASE_CANCELLATION = "purchase_cancellation"
    PRODUCTION_CONSUMPTION = "production_consumption"
    PRODUCTION_OUTPUT = "production_output"
    PACKAGING = "packaging"
    SALE = "sale"
    SALE_CANCELLATION = "sale_cancellation"
    INTERNAL_CONSUMPTION = "internal_consumption"
    TASTING = "tasting"
    DEVELOPMENT = "development"
    DISCARD = "discard"
    ADJUSTMENT = "adjustment"


@dataclass(frozen=True)
class InventoryMovementDraft:
    resource_id: UUID
    type: MovementType
    quantity: Decimal
    unit: UnitType
    reason: str


@dataclass(frozen=True)
class ProductionPlan:
    product_resource_id: UUID
    formula_id: UUID
    target_weight: Decimal
    unit: UnitType
    movements: list[InventoryMovementDraft]
