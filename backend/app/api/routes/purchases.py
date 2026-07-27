from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.auth import audit_user_id, require_roles
from app.db.models import (
    InventoryMovementModel,
    PurchaseDetailModel,
    PurchaseModel,
    PurchaseStatus,
    ResourceCostModel,
    ResourceModel,
    SupplierModel,
    UserRole,
)
from app.db.session import get_db
from app.domain.production.entities import MovementType
from app.schemas.auth import AuthenticatedUser
from app.schemas.purchases import (
    PurchaseCancel,
    PurchaseCreate,
    PurchaseLineRead,
    PurchaseMovementRead,
    PurchaseOptions,
    PurchaseRead,
    SupplierRead,
)

router = APIRouter()
MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def next_purchase_code(db: Session, organization_id: UUID, purchase_date: date) -> str:
    db.execute(text("lock table purchases in share row exclusive mode"))
    count = db.scalar(
        select(func.count())
        .select_from(PurchaseModel)
        .where(
            PurchaseModel.organization_id == organization_id,
            func.extract("year", PurchaseModel.purchase_date) == purchase_date.year,
        )
    )
    return f"C-{purchase_date.year}-{(count or 0) + 1:04d}"


def get_or_create_supplier(db: Session, organization_id: UUID, supplier_name: str) -> SupplierModel:
    cleaned_name = supplier_name.strip()
    supplier = db.scalar(
        select(SupplierModel).where(
            SupplierModel.organization_id == organization_id,
            func.lower(SupplierModel.name) == cleaned_name.lower(),
        )
    )
    if supplier:
        return supplier

    supplier = SupplierModel(
        organization_id=organization_id,
        name=cleaned_name,
        active=True,
    )
    db.add(supplier)
    db.flush()
    return supplier


def current_stock(db: Session, organization_id: UUID, resource_id: UUID) -> Decimal:
    return Decimal(
        str(
            db.scalar(
                select(func.coalesce(func.sum(InventoryMovementModel.quantity), 0)).where(
                    InventoryMovementModel.organization_id == organization_id,
                    InventoryMovementModel.resource_id == resource_id,
                )
            )
            or 0
        )
    )


def purchase_to_read(db: Session, purchase: PurchaseModel, include_movements: bool = False) -> PurchaseRead:
    resource_ids = [detail.resource_id for detail in purchase.details]
    resources = (
        db.scalars(select(ResourceModel).where(ResourceModel.id.in_(resource_ids))).all()
        if resource_ids
        else []
    )
    names = {resource.id: resource.name for resource in resources}

    lines = [
        PurchaseLineRead(
            id=detail.id,
            resource_id=detail.resource_id,
            resource_name=names.get(detail.resource_id, "Recurso no encontrado"),
            quantity=detail.quantity,
            unit=detail.unit,
            unit_price=detail.unit_price,
            line_total=detail.line_total,
        )
        for detail in purchase.details
    ]

    movements: list[PurchaseMovementRead] = []
    if include_movements:
        rows = db.execute(
            select(InventoryMovementModel, ResourceModel.name)
            .join(ResourceModel, ResourceModel.id == InventoryMovementModel.resource_id)
            .where(InventoryMovementModel.purchase_id == purchase.id)
            .order_by(InventoryMovementModel.created_at)
        ).all()
        movements = [
            PurchaseMovementRead(
                id=movement.id,
                resource_id=movement.resource_id,
                resource_name=resource_name,
                type=movement.type.value if hasattr(movement.type, "value") else str(movement.type),
                quantity=movement.quantity,
                unit_cost_snapshot=movement.unit_cost_snapshot,
                occurred_at=movement.occurred_at,
            )
            for movement, resource_name in rows
        ]

    return PurchaseRead(
        id=purchase.id,
        code=purchase.code,
        purchase_date=purchase.purchase_date,
        supplier_name=purchase.supplier_name,
        receipt_number=purchase.receipt_number,
        status=purchase.status.value if hasattr(purchase.status, "value") else str(purchase.status),
        subtotal=purchase.subtotal,
        total=purchase.total,
        notes=purchase.notes,
        confirmed_at=purchase.confirmed_at,
        cancelled_at=purchase.cancelled_at,
        cancellation_reason=purchase.cancellation_reason,
        lines=lines,
        movements=movements,
    )


@router.get("/options", response_model=PurchaseOptions)
def purchase_options(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    suppliers = db.scalars(
        select(SupplierModel)
        .where(SupplierModel.organization_id == organization_id, SupplierModel.active.is_(True))
        .order_by(SupplierModel.name)
    ).all()
    return PurchaseOptions(suppliers=[SupplierRead(id=supplier.id, name=supplier.name) for supplier in suppliers])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PurchaseRead)
def create_purchase(
    payload: PurchaseCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        resource_ids = sorted({line.resource_id for line in payload.lines}, key=str)
        resources = db.scalars(select(ResourceModel).where(ResourceModel.id.in_(resource_ids))).all()
        resources_by_id = {resource.id: resource for resource in resources}

        for line in payload.lines:
            resource = resources_by_id.get(line.resource_id)
            if resource is None or resource.organization_id != payload.organization_id:
                raise HTTPException(status_code=422, detail="Uno de los recursos seleccionados no existe.")
            if not resource.active:
                raise HTTPException(status_code=422, detail=f"{resource.name} esta inactivo y no puede comprarse.")
            if resource.unit != line.unit:
                raise HTTPException(
                    status_code=422,
                    detail=f"La unidad de {resource.name} debe ser {resource.unit.value}.",
                )

        code = next_purchase_code(db, payload.organization_id, payload.purchase_date)
        supplier = get_or_create_supplier(db, payload.organization_id, payload.supplier_name)
        total = money(sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0")))
        purchase = PurchaseModel(
            organization_id=payload.organization_id,
            code=code,
            purchase_date=payload.purchase_date,
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            receipt_number=payload.receipt_number,
            status=PurchaseStatus.DRAFT,
            subtotal=total,
            total=total,
            notes=payload.notes,
            created_by_user_id=audit_user_id(user),
        )
        db.add(purchase)
        db.flush()

        for line in payload.lines:
            db.add(
                PurchaseDetailModel(
                    organization_id=payload.organization_id,
                    purchase_id=purchase.id,
                    resource_id=line.resource_id,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_price=line.unit_price,
                    line_total=money(line.quantity * line.unit_price),
                )
            )

        db.commit()
        purchase = db.scalar(
            select(PurchaseModel)
            .options(selectinload(PurchaseModel.details))
            .where(PurchaseModel.id == purchase.id)
        )
        return purchase_to_read(db, purchase)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear la compra por una restriccion de datos.") from exc


@router.get("", response_model=list[PurchaseRead])
def list_purchases(
    organization_id: UUID = Query(...),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    stmt = (
        select(PurchaseModel)
        .options(selectinload(PurchaseModel.details))
        .where(PurchaseModel.organization_id == organization_id)
        .order_by(PurchaseModel.purchase_date.desc(), PurchaseModel.created_at.desc())
    )
    if status_filter:
        try:
            stmt = stmt.where(PurchaseModel.status == PurchaseStatus(status_filter))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="El estado seleccionado no es valido.") from exc
    return [purchase_to_read(db, purchase) for purchase in db.scalars(stmt).all()]


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(
    purchase_id: UUID,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    purchase = db.scalar(
        select(PurchaseModel)
        .options(selectinload(PurchaseModel.details))
        .where(PurchaseModel.id == purchase_id, PurchaseModel.organization_id == organization_id)
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada.")
    return purchase_to_read(db, purchase, include_movements=True)


@router.post("/{purchase_id}/confirm", response_model=PurchaseRead)
def confirm_purchase(
    purchase_id: UUID,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    purchase = db.scalar(
        select(PurchaseModel)
        .options(selectinload(PurchaseModel.details))
        .where(PurchaseModel.id == purchase_id, PurchaseModel.organization_id == organization_id)
        .with_for_update()
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada.")
    if purchase.status == PurchaseStatus.CONFIRMED:
        raise HTTPException(status_code=422, detail="Esta compra ya estaba confirmada.")
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(status_code=422, detail="No se puede confirmar una compra anulada.")
    if not purchase.details:
        raise HTTPException(status_code=422, detail="No se puede confirmar una compra sin lineas.")

    resource_ids = sorted({detail.resource_id for detail in purchase.details}, key=str)
    resources = db.scalars(
        select(ResourceModel)
        .where(ResourceModel.id.in_(resource_ids))
        .order_by(ResourceModel.id)
        .with_for_update()
    ).all()
    resources_by_id = {resource.id: resource for resource in resources}

    try:
        for detail in purchase.details:
            resource = resources_by_id.get(detail.resource_id)
            if resource is None or resource.organization_id != organization_id:
                raise HTTPException(status_code=422, detail="Uno de los recursos de la compra ya no existe.")
            if not resource.active:
                raise HTTPException(status_code=422, detail=f"{resource.name} esta inactivo y no puede confirmarse.")
            movement = InventoryMovementModel(
                organization_id=organization_id,
                resource_id=detail.resource_id,
                purchase_id=purchase.id,
                type=MovementType.PURCHASE,
                quantity=detail.quantity,
                unit=detail.unit,
                unit_cost_snapshot=detail.unit_price,
                reason=f"Compra {purchase.code}",
                occurred_at=datetime.combine(purchase.purchase_date, datetime.min.time(), tzinfo=timezone.utc),
                created_by_user_id=audit_user_id(user),
            )
            db.add(movement)
            db.add(
                ResourceCostModel(
                    organization_id=organization_id,
                    resource_id=detail.resource_id,
                    purchase_id=purchase.id,
                    amount=detail.unit_price,
                    unit=detail.unit,
                    supplier_name=purchase.supplier_name,
                    effective_date=purchase.purchase_date,
                    source="purchase",
                    notes=f"Compra {purchase.code}",
                )
            )

        purchase.status = PurchaseStatus.CONFIRMED
        purchase.confirmed_at = datetime.now(timezone.utc)
        purchase.confirmed_by_user_id = audit_user_id(user)
        purchase.updated_at = datetime.now(timezone.utc)
        db.commit()
        purchase = db.scalar(
            select(PurchaseModel)
            .options(selectinload(PurchaseModel.details))
            .where(PurchaseModel.id == purchase_id)
        )
        return purchase_to_read(db, purchase, include_movements=True)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo confirmar la compra. No se actualizo stock.") from exc


@router.post("/{purchase_id}/cancel", response_model=PurchaseRead)
def cancel_purchase(
    purchase_id: UUID,
    payload: PurchaseCancel,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    purchase = db.scalar(
        select(PurchaseModel)
        .options(selectinload(PurchaseModel.details))
        .where(PurchaseModel.id == purchase_id, PurchaseModel.organization_id == organization_id)
        .with_for_update()
    )
    if purchase is None:
        raise HTTPException(status_code=404, detail="Compra no encontrada.")
    if purchase.status == PurchaseStatus.CANCELLED:
        raise HTTPException(status_code=422, detail="Esta compra ya estaba anulada.")

    reason = (payload.reason or "").strip() or "Anulacion de compra"
    now = datetime.now(timezone.utc)

    try:
        if purchase.status == PurchaseStatus.CONFIRMED:
            resource_ids = sorted({detail.resource_id for detail in purchase.details}, key=str)
            resources = db.scalars(
                select(ResourceModel)
                .where(ResourceModel.id.in_(resource_ids))
                .order_by(ResourceModel.id)
                .with_for_update()
            ).all()
            resources_by_id = {resource.id: resource for resource in resources}

            for detail in purchase.details:
                resource = resources_by_id.get(detail.resource_id)
                if resource is None:
                    raise HTTPException(status_code=422, detail="Uno de los recursos de la compra ya no existe.")
                available = current_stock(db, organization_id, detail.resource_id)
                if available < detail.quantity:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"No se puede anular la compra: {resource.name} ya fue consumido o vendido "
                            "y el stock quedaria negativo."
                        ),
                    )

            for detail in purchase.details:
                db.add(
                    InventoryMovementModel(
                        organization_id=organization_id,
                        resource_id=detail.resource_id,
                        purchase_id=purchase.id,
                        type=MovementType.PURCHASE_CANCELLATION,
                        quantity=-detail.quantity,
                        unit=detail.unit,
                        unit_cost_snapshot=detail.unit_price,
                        reason=f"Anulacion de {purchase.code}: {reason}",
                        occurred_at=now,
                        created_by_user_id=audit_user_id(user),
                    )
                )
            db.query(ResourceCostModel).filter(
                ResourceCostModel.organization_id == organization_id,
                ResourceCostModel.purchase_id == purchase.id,
                ResourceCostModel.source == "purchase",
            ).update({ResourceCostModel.active: False}, synchronize_session=False)

        purchase.status = PurchaseStatus.CANCELLED
        purchase.cancelled_at = now
        purchase.cancelled_by_user_id = audit_user_id(user)
        purchase.cancellation_reason = reason
        purchase.updated_at = now
        db.commit()
        purchase = db.scalar(
            select(PurchaseModel)
            .options(selectinload(PurchaseModel.details))
            .where(PurchaseModel.id == purchase_id)
        )
        return purchase_to_read(db, purchase, include_movements=True)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo anular la compra.") from exc
