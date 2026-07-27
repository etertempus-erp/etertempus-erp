from decimal import Decimal
from uuid import UUID

from app.domain.formulas.entities import Formula
from app.domain.formulas.services import calculate_formula_grams
from app.domain.production.entities import InventoryMovementDraft, MovementType, ProductionPlan
from app.domain.resources.entities import UnitType


def build_production_plan(
    formula: Formula,
    product_resource_id: UUID,
    mix_resource_id: UUID,
    target_weight: Decimal,
) -> ProductionPlan:
    grams_by_resource = calculate_formula_grams(formula.items, target_weight)

    movements: list[InventoryMovementDraft] = []
    for resource_id, grams in grams_by_resource.items():
        movements.append(
            InventoryMovementDraft(
                resource_id=UUID(resource_id),
                type=MovementType.PRODUCTION_CONSUMPTION,
                quantity=-grams,
                unit=UnitType.G,
                reason="Consumo de materia prima para elaboracion",
            )
        )

    movements.append(
        InventoryMovementDraft(
            resource_id=mix_resource_id,
            type=MovementType.PRODUCTION_OUTPUT,
            quantity=target_weight,
            unit=UnitType.G,
            reason="Mezcla elaborada",
        )
    )

    return ProductionPlan(
        product_resource_id=product_resource_id,
        formula_id=formula.id,
        target_weight=target_weight,
        unit=UnitType.G,
        movements=movements,
    )

