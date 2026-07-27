from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.db.models import UserRole
from app.db.repositories import SqlAlchemyFormulaRepository
from app.db.session import get_db
from app.domain.formulas.services import calculate_formula_grams
from app.schemas.formulas import FormulaCreate, FormulaDetail, FormulaScaleRequest, FormulaSummary
from app.use_cases.create_formula import CreateFormula

router = APIRouter()


@router.get("", response_model=list[FormulaSummary])
def list_formulas(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyFormulaRepository(db)
    return repository.list(organization_id=organization_id)


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles(UserRole.ADMIN))])
def create_formula(payload: FormulaCreate, db: Session = Depends(get_db)):
    repository = SqlAlchemyFormulaRepository(db)
    use_case = CreateFormula(repository)

    try:
        formula_id = use_case.execute(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una formula con ese nombre y version.",
        ) from exc

    return {"id": formula_id}


@router.get("/{formula_id}", response_model=FormulaDetail)
def get_formula(
    formula_id: UUID,
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyFormulaRepository(db)
    try:
        return repository.detail(formula_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{formula_id}/scale")
def scale_formula(
    formula_id: UUID,
    payload: FormulaScaleRequest,
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyFormulaRepository(db)
    try:
        formula = repository.get(formula_id)
        ingredient_grams = calculate_formula_grams(formula.items, payload.target_weight)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return {
        "formula_id": formula_id,
        "target_weight": payload.target_weight,
        "ingredient_grams": ingredient_grams,
    }
