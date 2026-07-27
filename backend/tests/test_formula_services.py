from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.formulas.entities import FormulaItem
from app.domain.formulas.services import calculate_formula_grams, validate_formula_percentages


def test_formula_must_sum_100_percent():
    items = [
        FormulaItem(ingredient_resource_id=uuid4(), percentage=Decimal("60")),
        FormulaItem(ingredient_resource_id=uuid4(), percentage=Decimal("30")),
    ]

    with pytest.raises(ValueError):
        validate_formula_percentages(items)


def test_calculates_grams_from_percentages():
    ingredient = uuid4()
    items = [FormulaItem(ingredient_resource_id=ingredient, percentage=Decimal("25"))]

    with pytest.raises(ValueError):
        calculate_formula_grams(items, Decimal("400"))

    items.append(FormulaItem(ingredient_resource_id=uuid4(), percentage=Decimal("75")))
    result = calculate_formula_grams(items, Decimal("400"))

    assert result[str(ingredient)] == Decimal("100.000")

