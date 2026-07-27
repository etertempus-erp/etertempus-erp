from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ResourceType(StrEnum):
    RAW_MATERIAL = "raw_material"
    PACKAGING = "packaging"
    PRODUCT = "product"
    MIX = "mix"


class UnitType(StrEnum):
    G = "g"
    KG = "kg"
    ML = "ml"
    UNIT = "unit"


@dataclass(frozen=True)
class Resource:
    id: UUID
    organization_id: UUID
    code: str
    name: str
    type: ResourceType
    unit: UnitType
    minimum_stock: Decimal
    active: bool = True
    latest_unit_cost: Decimal | None = None
    latest_supplier_name: str | None = None
