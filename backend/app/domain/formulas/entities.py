from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class FormulaStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class FormulaItem:
    ingredient_resource_id: UUID
    percentage: Decimal
    sort_order: int = 0


@dataclass(frozen=True)
class Formula:
    id: UUID
    organization_id: UUID
    name: str
    version: int
    status: FormulaStatus
    items: list[FormulaItem]
    product_resource_id: UUID | None = None
    active_version: bool = False
    notes: str | None = None

