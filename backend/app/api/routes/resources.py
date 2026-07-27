from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.repositories import SqlAlchemyResourceRepository
from app.db.session import get_db
from app.domain.resources.entities import ResourceType
from app.schemas.resources import (
    ResourceCreate,
    ResourceRead,
    ResourceStockRead,
    ResourceUpdate,
    StockAdjustmentCreate,
    StockSetCreate,
)
from app.use_cases.create_resource import CreateResource

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def create_resource(payload: ResourceCreate, db: Session = Depends(get_db)):
    repository = SqlAlchemyResourceRepository(db)
    use_case = CreateResource(repository)

    try:
        resource_id = use_case.execute(
            organization_id=payload.organization_id,
            code=payload.code,
            name=payload.name,
            type=payload.type,
            unit=payload.unit,
            minimum_stock=payload.minimum_stock,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un recurso con ese codigo para esta organizacion.",
        ) from exc

    return {"id": resource_id}


@router.get("", response_model=list[ResourceRead])
def list_resources(
    organization_id: UUID = Query(...),
    type: ResourceType | None = Query(default=None),
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyResourceRepository(db)
    return repository.list(organization_id=organization_id, type=type)


@router.put("/{resource_id}", response_model=ResourceRead)
def update_resource(
    resource_id: UUID,
    payload: ResourceUpdate,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyResourceRepository(db)

    try:
        return repository.update(
            organization_id=organization_id,
            resource_id=resource_id,
            code=payload.code,
            name=payload.name,
            type=payload.type,
            unit=payload.unit,
            minimum_stock=payload.minimum_stock,
            active=payload.active,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe otro recurso con ese codigo para esta organizacion.",
        ) from exc


@router.get("/stock", response_model=list[ResourceStockRead])
def list_stock(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyResourceRepository(db)
    return repository.stock(organization_id=organization_id)


@router.post("/{resource_id}/stock-adjustments", status_code=status.HTTP_201_CREATED)
def add_stock_adjustment(
    resource_id: UUID,
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyResourceRepository(db)

    try:
        movement_id = repository.add_stock_adjustment(
            organization_id=payload.organization_id,
            resource_id=resource_id,
            quantity=payload.quantity,
            unit=payload.unit,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {"id": movement_id}


@router.post("/{resource_id}/stock", status_code=status.HTTP_201_CREATED)
def set_current_stock(
    resource_id: UUID,
    payload: StockSetCreate,
    db: Session = Depends(get_db),
):
    repository = SqlAlchemyResourceRepository(db)

    try:
        return repository.set_current_stock(
            organization_id=payload.organization_id,
            resource_id=resource_id,
            quantity=payload.quantity,
            unit=payload.unit,
            reason=payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
