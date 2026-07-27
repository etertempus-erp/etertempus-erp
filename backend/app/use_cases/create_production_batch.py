from app.domain.production.services import build_production_plan
from app.schemas.production import ProductionBatchCreate
from app.use_cases.repositories import FormulaRepository, ProductionRepository


class CreateProductionBatch:
    def __init__(
        self,
        formulas: FormulaRepository,
        production: ProductionRepository,
    ) -> None:
        self.formulas = formulas
        self.production = production

    def execute(self, payload: ProductionBatchCreate):
        formula = self.formulas.get(payload.formula_id)
        batch_number = self.production.next_batch_number(payload.organization_id)
        mix_resource_id = self.production.create_mix_resource(
            organization_id=payload.organization_id,
            batch_number=batch_number,
            product_resource_id=payload.product_resource_id,
        )
        plan = build_production_plan(
            formula=formula,
            product_resource_id=payload.product_resource_id,
            mix_resource_id=mix_resource_id,
            target_weight=payload.target_weight,
        )
        return self.production.create_batch_with_movements(
            organization_id=payload.organization_id,
            batch_number=batch_number,
            elaboration_date=payload.elaboration_date,
            product_resource_id=payload.product_resource_id,
            formula_id=payload.formula_id,
            mix_resource_id=mix_resource_id,
            target_weight=plan.target_weight,
            movements=plan.movements,
            notes=payload.notes,
        )
