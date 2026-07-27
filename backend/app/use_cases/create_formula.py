from uuid import uuid4

from app.domain.formulas.entities import Formula, FormulaItem
from app.domain.formulas.services import validate_formula_percentages
from app.schemas.formulas import FormulaCreate
from app.use_cases.repositories import FormulaRepository


class CreateFormula:
    def __init__(self, formulas: FormulaRepository) -> None:
        self.formulas = formulas

    def execute(self, payload: FormulaCreate):
        items = [
            FormulaItem(
                ingredient_resource_id=item.ingredient_resource_id,
                percentage=item.percentage,
                sort_order=item.sort_order,
            )
            for item in payload.items
        ]
        validate_formula_percentages(items)

        formula = Formula(
            id=uuid4(),
            organization_id=payload.organization_id,
            product_resource_id=payload.product_resource_id,
            name=payload.name.strip(),
            version=payload.version,
            status=payload.status,
            active_version=payload.active_version,
            notes=payload.notes,
            items=items,
        )
        return self.formulas.create(formula)

