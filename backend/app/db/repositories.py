from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    FormulaItemModel,
    FormulaModel,
    InventoryMovementModel,
    ProductionBatchModel,
    PurchaseModel,
    PurchaseStatus,
    ResourceCostModel,
    ResourceModel,
    current_stock_query,
)
from app.domain.formulas.entities import Formula, FormulaItem
from app.domain.production.entities import BatchStatus, InventoryMovementDraft, MovementType
from app.domain.resources.entities import Resource, ResourceType, UnitType
from app.use_cases.repositories import FormulaRepository, ProductionRepository, ResourceRepository


class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        organization_id: UUID,
        code: str,
        name: str,
        type: ResourceType,
        unit: UnitType,
        minimum_stock: Decimal,
    ) -> UUID:
        model = ResourceModel(
            organization_id=organization_id,
            code=code,
            name=name,
            type=type,
            unit=unit,
            minimum_stock=minimum_stock,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model.id

    def list(self, organization_id: UUID, type: ResourceType | None = None) -> list[Resource]:
        stmt = select(ResourceModel).where(ResourceModel.organization_id == organization_id)
        if type is not None:
            stmt = stmt.where(ResourceModel.type == type)
        stmt = stmt.order_by(ResourceModel.type, ResourceModel.name)
        models = self.db.scalars(stmt).all()

        resources = []
        for model in models:
            latest_cost = self.db.scalar(
                select(ResourceCostModel)
                .where(
                    ResourceCostModel.organization_id == organization_id,
                    ResourceCostModel.resource_id == model.id,
                    ResourceCostModel.active.is_(True),
                    ~(
                        select(PurchaseModel.id)
                        .where(
                            PurchaseModel.id == ResourceCostModel.purchase_id,
                            PurchaseModel.status == PurchaseStatus.CANCELLED,
                        )
                        .exists()
                    ),
                )
                .order_by(
                    ResourceCostModel.effective_date.desc().nullslast(),
                    ResourceCostModel.created_at.desc(),
                )
                .limit(1)
            )
            resources.append(
                Resource(
                    id=model.id,
                    organization_id=model.organization_id,
                    code=model.code,
                    name=model.name,
                    type=model.type,
                    unit=model.unit,
                    minimum_stock=model.minimum_stock,
                    active=model.active,
                    latest_unit_cost=latest_cost.amount if latest_cost else None,
                    latest_supplier_name=latest_cost.supplier_name if latest_cost else None,
                )
            )
        return resources

    def update(
        self,
        organization_id: UUID,
        resource_id: UUID,
        code: str,
        name: str,
        type: ResourceType,
        unit: UnitType,
        minimum_stock: Decimal,
        active: bool,
    ) -> Resource:
        model = self.db.get(ResourceModel, resource_id)
        if model is None or model.organization_id != organization_id:
            raise LookupError("Recurso no encontrado.")

        model.code = code
        model.name = name
        model.type = type
        model.unit = unit
        model.minimum_stock = minimum_stock
        model.active = active
        self.db.commit()
        self.db.refresh(model)

        return Resource(
            id=model.id,
            organization_id=model.organization_id,
            code=model.code,
            name=model.name,
            type=model.type,
            unit=model.unit,
            minimum_stock=model.minimum_stock,
            active=model.active,
        )

    def add_stock_adjustment(
        self,
        organization_id: UUID,
        resource_id: UUID,
        quantity: Decimal,
        unit: UnitType,
        reason: str,
    ) -> UUID:
        resource = self.db.get(ResourceModel, resource_id)
        if resource is None:
            raise LookupError("Recurso no encontrado.")
        if resource.organization_id != organization_id:
            raise LookupError("El recurso no pertenece a la organizacion indicada.")

        movement = InventoryMovementModel(
            organization_id=organization_id,
            resource_id=resource_id,
            type=MovementType.ADJUSTMENT,
            quantity=quantity,
            unit=unit,
            reason=reason,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement.id

    def set_current_stock(
        self,
        organization_id: UUID,
        resource_id: UUID,
        quantity: Decimal,
        unit: UnitType,
        reason: str,
    ) -> dict:
        resource = self.db.get(ResourceModel, resource_id)
        if resource is None:
            raise LookupError("Recurso no encontrado.")
        if resource.organization_id != organization_id:
            raise LookupError("El recurso no pertenece a la organizacion indicada.")
        if resource.unit != unit:
            raise ValueError("La unidad indicada no coincide con la unidad del recurso.")

        current_quantity = Decimal(self.db.scalar(current_stock_query(resource_id)) or 0)
        adjustment = quantity - current_quantity
        if adjustment == 0:
            return {
                "movement_id": None,
                "previous_quantity": current_quantity,
                "new_quantity": quantity,
                "adjustment": adjustment,
            }

        movement = InventoryMovementModel(
            organization_id=organization_id,
            resource_id=resource_id,
            type=MovementType.ADJUSTMENT,
            quantity=adjustment,
            unit=unit,
            reason=reason,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return {
            "movement_id": movement.id,
            "previous_quantity": current_quantity,
            "new_quantity": quantity,
            "adjustment": adjustment,
        }

    def stock(self, organization_id: UUID) -> list[dict]:
        stmt = (
            select(
                ResourceModel.id,
                ResourceModel.code,
                ResourceModel.name,
                ResourceModel.type,
                ResourceModel.unit,
                func.coalesce(func.sum(InventoryMovementModel.quantity), 0).label("quantity"),
            )
            .outerjoin(InventoryMovementModel, InventoryMovementModel.resource_id == ResourceModel.id)
            .where(ResourceModel.organization_id == organization_id)
            .group_by(
                ResourceModel.id,
                ResourceModel.code,
                ResourceModel.name,
                ResourceModel.type,
                ResourceModel.unit,
            )
            .order_by(ResourceModel.type, ResourceModel.name)
        )
        return [
            {
                "resource_id": row.id,
                "code": row.code,
                "name": row.name,
                "type": row.type,
                "unit": row.unit,
                "quantity": row.quantity,
            }
            for row in self.db.execute(stmt)
        ]


class SqlAlchemyFormulaRepository(FormulaRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, formula_id: UUID) -> Formula:
        model = self.db.scalar(
            select(FormulaModel)
            .options(selectinload(FormulaModel.items))
            .where(FormulaModel.id == formula_id)
        )
        if model is None:
            raise LookupError("Formula no encontrada.")

        return Formula(
            id=model.id,
            organization_id=model.organization_id,
            product_resource_id=model.product_resource_id,
            name=model.name,
            version=model.version,
            status=model.status,
            active_version=model.active_version,
            notes=model.notes,
            items=[
                FormulaItem(
                    ingredient_resource_id=item.ingredient_resource_id,
                    percentage=item.percentage,
                    sort_order=item.sort_order,
                )
                for item in model.items
            ],
        )

    def create(self, formula: Formula) -> UUID:
        model = FormulaModel(
            id=formula.id,
            organization_id=formula.organization_id,
            product_resource_id=formula.product_resource_id,
            name=formula.name,
            version=formula.version,
            status=formula.status,
            active_version=formula.active_version,
            notes=formula.notes,
            items=[
                FormulaItemModel(
                    ingredient_resource_id=item.ingredient_resource_id,
                    percentage=item.percentage,
                    sort_order=item.sort_order,
                )
                for item in formula.items
            ],
        )
        self.db.add(model)
        self.db.commit()
        return model.id

    def list(self, organization_id: UUID) -> list[dict]:
        stmt = (
            select(FormulaModel)
            .where(FormulaModel.organization_id == organization_id)
            .order_by(FormulaModel.name, FormulaModel.version.desc())
        )
        return [
            {
                "id": model.id,
                "organization_id": model.organization_id,
                "product_resource_id": model.product_resource_id,
                "name": model.name,
                "version": model.version,
                "status": model.status,
                "active_version": model.active_version,
            }
            for model in self.db.scalars(stmt).all()
        ]

    def detail(self, formula_id: UUID) -> dict:
        model = self.db.scalar(
            select(FormulaModel)
            .options(selectinload(FormulaModel.items))
            .where(FormulaModel.id == formula_id)
        )
        if model is None:
            raise LookupError("Formula no encontrada.")

        ingredient_ids = [item.ingredient_resource_id for item in model.items]
        ingredient_rows = self.db.scalars(
            select(ResourceModel).where(ResourceModel.id.in_(ingredient_ids))
        ).all()
        names_by_id = {resource.id: resource.name for resource in ingredient_rows}

        return {
            "id": model.id,
            "organization_id": model.organization_id,
            "product_resource_id": model.product_resource_id,
            "name": model.name,
            "version": model.version,
            "status": model.status,
            "active_version": model.active_version,
            "notes": model.notes,
            "items": [
                {
                    "ingredient_resource_id": item.ingredient_resource_id,
                    "ingredient_name": names_by_id.get(item.ingredient_resource_id, "Ingrediente no encontrado"),
                    "percentage": item.percentage,
                    "sort_order": item.sort_order,
                }
                for item in model.items
            ],
        }


class SqlAlchemyProductionRepository(ProductionRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def next_batch_number(self, organization_id: UUID) -> str:
        year = date.today().year
        count = self.db.scalar(
            select(func.count())
            .select_from(ProductionBatchModel)
            .where(ProductionBatchModel.organization_id == organization_id)
        )
        return f"LT-{year}-{(count or 0) + 1:04d}"

    def create_mix_resource(
        self,
        organization_id: UUID,
        batch_number: str,
        product_resource_id: UUID,
    ) -> UUID:
        product = self.db.get(ResourceModel, product_resource_id)
        if product is None:
            raise LookupError("Producto no encontrado.")

        mix = ResourceModel(
            organization_id=organization_id,
            code=f"MIX-{batch_number}",
            name=f"Mezcla {batch_number} - {product.name}",
            type=ResourceType.MIX,
            unit=UnitType.G,
            minimum_stock=Decimal("0"),
        )
        self.db.add(mix)
        self.db.flush()
        return mix.id

    def create_batch_with_movements(
        self,
        organization_id: UUID,
        batch_number: str,
        elaboration_date: date,
        product_resource_id: UUID,
        formula_id: UUID,
        mix_resource_id: UUID,
        target_weight: Decimal,
        movements: list[InventoryMovementDraft],
        notes: str | None = None,
    ) -> UUID:
        for movement in movements:
            if movement.quantity < 0:
                available = self.db.scalar(current_stock_query(movement.resource_id)) or Decimal("0")
                if available + movement.quantity < 0:
                    raise ValueError(
                        f"Stock insuficiente para el recurso {movement.resource_id}. "
                        f"Disponible: {available}, requerido: {-movement.quantity}."
                    )

        batch_id = uuid4()
        batch = ProductionBatchModel(
            id=batch_id,
            organization_id=organization_id,
            batch_number=batch_number,
            elaboration_date=elaboration_date,
            product_resource_id=product_resource_id,
            formula_id=formula_id,
            mix_resource_id=mix_resource_id,
            target_weight=target_weight,
            unit=UnitType.G,
            status=BatchStatus.ELABORATED,
            notes=notes,
        )
        self.db.add(batch)
        self.db.flush()

        for movement in movements:
            self.db.add(
                InventoryMovementModel(
                    organization_id=organization_id,
                    resource_id=movement.resource_id,
                    production_batch_id=batch_id,
                    type=movement.type,
                    quantity=movement.quantity,
                    unit=movement.unit,
                    reason=movement.reason,
                )
            )

        self.db.commit()
        return batch_id

    def list_batches(self, organization_id: UUID) -> list[dict]:
        stmt = (
            select(ProductionBatchModel)
            .where(ProductionBatchModel.organization_id == organization_id)
            .order_by(ProductionBatchModel.elaboration_date.desc(), ProductionBatchModel.batch_number.desc())
        )
        return [
            {
                "id": model.id,
                "batch_number": model.batch_number,
                "product_resource_id": model.product_resource_id,
                "formula_id": model.formula_id,
                "mix_resource_id": model.mix_resource_id,
                "elaboration_date": model.elaboration_date,
                "target_weight": model.target_weight,
                "status": model.status.value,
            }
            for model in self.db.scalars(stmt).all()
        ]
