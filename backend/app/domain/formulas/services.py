from decimal import Decimal, ROUND_HALF_UP

from app.domain.formulas.entities import FormulaItem


def validate_formula_percentages(items: list[FormulaItem]) -> None:
    total = sum((item.percentage for item in items), Decimal("0"))
    if total != Decimal("100"):
        raise ValueError(f"La formula debe sumar 100%. Suma actual: {total}.")


def calculate_formula_grams(
    items: list[FormulaItem],
    target_weight: Decimal,
) -> dict[str, Decimal]:
    if target_weight <= 0:
        raise ValueError("El peso objetivo debe ser mayor a cero.")

    validate_formula_percentages(items)

    grams_by_resource: dict[str, Decimal] = {}
    for item in items:
        grams = (target_weight * item.percentage / Decimal("100")).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )
        grams_by_resource[str(item.ingredient_resource_id)] = grams

    return grams_by_resource

