from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import FormulaModel, ResourceModel
from app.db.repositories import SqlAlchemyFormulaRepository, SqlAlchemyProductionRepository
from app.db.session import get_db
from app.domain.resources.entities import ResourceType
from app.schemas.production import ProductionBatchCreate, ProductionBatchSummary
from app.use_cases.create_production_batch import CreateProductionBatch

router = APIRouter()


@router.get("/batches", response_model=list[ProductionBatchSummary])
def list_batches(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyProductionRepository(db)
    return repository.list_batches(organization_id=organization_id)


@router.post("/batches", status_code=status.HTTP_201_CREATED)
def create_batch(payload: ProductionBatchCreate, db: Session = Depends(get_db)):
    product = db.get(ResourceModel, payload.product_resource_id)
    if product is None or product.organization_id != payload.organization_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Selecciona un producto valido.")
    if product.type != ResourceType.PRODUCT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{product.name} no esta marcado como producto terminado.",
        )
    if not product.active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{product.name} esta inactivo y no puede producirse.",
        )

    formula = db.get(FormulaModel, payload.formula_id)
    if formula is None or formula.organization_id != payload.organization_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Selecciona una formula valida.")
    if formula.product_resource_id != payload.product_resource_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La formula seleccionada no pertenece al producto que quieres producir.",
        )

    use_case = CreateProductionBatch(
        formulas=SqlAlchemyFormulaRepository(db),
        production=SqlAlchemyProductionRepository(db),
    )

    try:
        batch_id = use_case.execute(payload)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear el lote por una restriccion de datos.",
        ) from exc

    return {"id": batch_id}
