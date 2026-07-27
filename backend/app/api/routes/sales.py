from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.auth import audit_user_id, require_roles
from app.db.models import (
    ImportedSaleModel,
    InventoryMovementModel,
    PaymentMethodModel,
    PointOfSaleModel,
    ProductPriceModel,
    ResourceModel,
    SaleDetailModel,
    SaleInventoryMovementModel,
    SaleModel,
    SalesChannelModel,
    SaleStatus,
    UserRole,
)
from app.db.session import get_db
from app.domain.production.entities import MovementType
from app.domain.resources.entities import ResourceType
from app.schemas.auth import AuthenticatedUser
from app.schemas.sales import (
    ProductForSale,
    SaleCancel,
    SaleCreate,
    SaleCreated,
    SaleLineRead,
    SaleMovementRead,
    SaleOption,
    SaleOptions,
    SaleRead,
)

router = APIRouter()

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def stock_for(db: Session, organization_id: UUID, resource_id: UUID) -> Decimal:
    return Decimal(
        db.execute(
            text(
                """
                select coalesce(sum(quantity), 0)
                from inventory_movements
                where organization_id = :organization_id
                  and resource_id = :resource_id
                """
            ),
            {"organization_id": organization_id, "resource_id": resource_id},
        ).scalar()
        or 0
    )


def next_sale_code(db: Session, organization_id: UUID, sale_date: date) -> str:
    db.execute(text("lock table sales in share row exclusive mode"))
    count = db.scalar(
        select(func.count())
        .select_from(SaleModel)
        .where(
            SaleModel.organization_id == organization_id,
            func.extract("year", SaleModel.sale_date) == sale_date.year,
        )
    )
    return f"V-{sale_date.year}-{(count or 0) + 1:04d}"


def channel_requires_point_of_sale(channel_name: str) -> bool:
    lowered = channel_name.lower()
    return "feria" in lowered or "punto" in lowered


def sale_to_read(
    db: Session,
    sale: SaleModel,
    include_movements: bool = False,
) -> SaleRead:
    channel = db.get(SalesChannelModel, sale.channel_id)
    payment = db.get(PaymentMethodModel, sale.payment_method_id)
    point = db.get(PointOfSaleModel, sale.point_of_sale_id) if sale.point_of_sale_id else None

    resource_ids = [detail.resource_id for detail in sale.details]
    resources = (
        db.scalars(select(ResourceModel).where(ResourceModel.id.in_(resource_ids))).all()
        if resource_ids
        else []
    )
    names = {resource.id: resource.name for resource in resources}

    lines = [
        SaleLineRead(
            id=detail.id,
            product_resource_id=detail.resource_id,
            product_name=names.get(detail.resource_id, "Producto no encontrado"),
            quantity=detail.quantity,
            unit_price=detail.unit_price,
            discount=detail.discount,
            line_total=detail.line_total,
        )
        for detail in sale.details
    ]

    movements: list[SaleMovementRead] = []
    if include_movements:
        rows = db.execute(
            select(InventoryMovementModel, ResourceModel.name)
            .join(ResourceModel, ResourceModel.id == InventoryMovementModel.resource_id)
            .join(
                SaleInventoryMovementModel,
                SaleInventoryMovementModel.inventory_movement_id == InventoryMovementModel.id,
            )
            .join(SaleDetailModel, SaleDetailModel.id == SaleInventoryMovementModel.sale_detail_id)
            .where(SaleDetailModel.sale_id == sale.id)
            .order_by(InventoryMovementModel.created_at)
        ).all()
        movements = [
            SaleMovementRead(
                id=movement.id,
                resource_id=movement.resource_id,
                resource_name=resource_name,
                type=movement.type.value if hasattr(movement.type, "value") else str(movement.type),
                quantity=movement.quantity,
                occurred_at=movement.occurred_at,
            )
            for movement, resource_name in rows
        ]

    return SaleRead(
        id=sale.id,
        code=sale.code,
        sale_date=sale.sale_date,
        channel_id=sale.channel_id,
        channel_name=channel.name if channel else None,
        point_of_sale_id=sale.point_of_sale_id,
        point_of_sale_name=point.name if point else None,
        customer_name=sale.customer_name,
        payment_method_id=sale.payment_method_id,
        payment_method_name=payment.name if payment else None,
        status=sale.status.value if hasattr(sale.status, "value") else str(sale.status),
        subtotal=sale.subtotal,
        discount_total=sale.discount_total,
        total=sale.total,
        notes=sale.notes,
        source=sale.source,
        quantity_total=sum((line.quantity for line in lines), Decimal("0")),
        products_summary=", ".join(f"{line.quantity:g} {line.product_name}" for line in lines),
        lines=lines,
        movements=movements,
    )


def imported_sale_to_read(row: ImportedSaleModel) -> SaleRead:
    quantity = row.quantity or Decimal("0")
    unit_price = row.unit_price or Decimal("0")
    total = row.total_amount or money(quantity * unit_price)
    return SaleRead(
        id=row.id,
        code=f"IMP-{row.source_row}",
        sale_date=row.sale_date,
        channel_name=row.channel_name,
        customer_name=row.customer_name,
        payment_method_name=row.payment_method,
        status="imported",
        subtotal=total,
        discount_total=Decimal("0"),
        total=total,
        notes=f"Importada desde {row.source_sheet}, fila {row.source_row}. No descuenta stock.",
        source="imported",
        quantity_total=quantity,
        products_summary=f"{quantity:g} {row.product_name}",
        lines=[
            SaleLineRead(
                id=row.id,
                product_resource_id=row.id,
                product_name=row.product_name,
                quantity=quantity,
                unit_price=unit_price,
                discount=Decimal("0"),
                line_total=total,
            )
        ],
        movements=[],
    )


@router.get("/options", response_model=SaleOptions)
def sale_options(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    channels = db.scalars(
        select(SalesChannelModel)
        .where(SalesChannelModel.organization_id == organization_id)
        .order_by(SalesChannelModel.name)
    ).all()
    payment_methods = db.scalars(
        select(PaymentMethodModel)
        .where(PaymentMethodModel.organization_id == organization_id, PaymentMethodModel.active.is_(True))
        .order_by(PaymentMethodModel.name)
    ).all()
    points = db.scalars(
        select(PointOfSaleModel)
        .where(PointOfSaleModel.organization_id == organization_id, PointOfSaleModel.active.is_(True))
        .order_by(PointOfSaleModel.name)
    ).all()

    return SaleOptions(
        channels=[SaleOption(id=item.id, name=item.name) for item in channels],
        payment_methods=[SaleOption(id=item.id, name=item.name) for item in payment_methods],
        points_of_sale=[SaleOption(id=item.id, name=item.name) for item in points],
    )


@router.get("/products/available-for-sale", response_model=list[ProductForSale])
def available_products(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    products = db.scalars(
        select(ResourceModel)
        .where(
            ResourceModel.organization_id == organization_id,
            ResourceModel.type == ResourceType.PRODUCT,
            ResourceModel.active.is_(True),
        )
        .order_by(ResourceModel.name)
    ).all()

    result: list[ProductForSale] = []
    for product in products:
        price = db.scalar(
            select(ProductPriceModel)
            .where(
                ProductPriceModel.organization_id == organization_id,
                ProductPriceModel.product_resource_id == product.id,
            )
            .order_by(
                ProductPriceModel.effective_date.desc().nullslast(),
                ProductPriceModel.created_at.desc(),
            )
            .limit(1)
        )
        result.append(
            ProductForSale(
                id=product.id,
                code=product.code,
                name=product.name,
                unit=product.unit.value if hasattr(product.unit, "value") else str(product.unit),
                available_stock=stock_for(db, organization_id, product.id),
                suggested_price=price.sale_price if price else None,
                price_list_name=price.price_list_name if price else None,
            )
        )
    return result


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SaleCreated)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN, UserRole.OPERATOR)),
):
    try:
        channel = db.get(SalesChannelModel, payload.channel_id)
        if channel is None or channel.organization_id != payload.organization_id:
            raise HTTPException(status_code=422, detail="Selecciona un canal de venta valido.")

        payment_method = db.get(PaymentMethodModel, payload.payment_method_id)
        if payment_method is None or payment_method.organization_id != payload.organization_id:
            raise HTTPException(status_code=422, detail="Selecciona un medio de pago valido.")

        if channel_requires_point_of_sale(channel.name) and payload.point_of_sale_id is None:
            raise HTTPException(status_code=422, detail="Selecciona el punto de venta para este canal.")

        if payload.point_of_sale_id is not None:
            point = db.get(PointOfSaleModel, payload.point_of_sale_id)
            if point is None or point.organization_id != payload.organization_id:
                raise HTTPException(status_code=422, detail="Selecciona un punto de venta valido.")

        product_ids = sorted({line.product_resource_id for line in payload.lines}, key=str)
        products = db.scalars(
            select(ResourceModel)
            .where(ResourceModel.id.in_(product_ids))
            .order_by(ResourceModel.id)
            .with_for_update()
        ).all()
        products_by_id = {product.id: product for product in products}

        required_by_product: dict[UUID, Decimal] = {}
        for line in payload.lines:
            product = products_by_id.get(line.product_resource_id)
            if product is None or product.organization_id != payload.organization_id:
                raise HTTPException(status_code=422, detail="Uno de los productos seleccionados no existe.")
            if product.type != ResourceType.PRODUCT:
                raise HTTPException(status_code=422, detail=f"{product.name} no esta marcado como producto vendible.")
            if not product.active:
                raise HTTPException(status_code=422, detail=f"{product.name} esta inactivo y no se puede vender.")
            required_by_product[line.product_resource_id] = (
                required_by_product.get(line.product_resource_id, Decimal("0")) + line.quantity
            )

        for product_id, required in required_by_product.items():
            available = stock_for(db, payload.organization_id, product_id)
            if available < required:
                product = products_by_id[product_id]
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Stock insuficiente para {product.name}. "
                        f"Disponible: {available:g}, requerido: {required:g}. "
                        "La venta no se registro y no se desconto stock."
                    ),
                )

        code = next_sale_code(db, payload.organization_id, payload.sale_date)
        subtotal = money(sum((line.quantity * line.unit_price for line in payload.lines), Decimal("0")))
        discount_total = money(sum((line.discount for line in payload.lines), Decimal("0")))
        total = money(subtotal - discount_total)

        sale = SaleModel(
            organization_id=payload.organization_id,
            code=code,
            sale_date=payload.sale_date,
            channel_id=payload.channel_id,
            point_of_sale_id=payload.point_of_sale_id,
            customer_name=payload.customer_name,
            payment_method_id=payload.payment_method_id,
            status=SaleStatus.CONFIRMED,
            subtotal=subtotal,
            discount_total=discount_total,
            total=total,
            notes=payload.notes,
            source="system",
            created_by=payload.created_by,
            created_by_user_id=audit_user_id(user),
            confirmed_at=datetime.now(timezone.utc),
        )
        db.add(sale)
        db.flush()

        remaining_stock: dict[UUID, Decimal] = {}
        for line in payload.lines:
            product = products_by_id[line.product_resource_id]
            line_total = money((line.quantity * line.unit_price) - line.discount)
            detail = SaleDetailModel(
                organization_id=payload.organization_id,
                sale_id=sale.id,
                resource_id=line.product_resource_id,
                quantity=line.quantity,
                unit_price=money(line.unit_price),
                discount=money(line.discount),
                line_total=line_total,
            )
            db.add(detail)
            db.flush()

            movement = InventoryMovementModel(
                organization_id=payload.organization_id,
                resource_id=line.product_resource_id,
                type=MovementType.SALE,
                quantity=-line.quantity,
                unit=product.unit,
                reason=f"Venta {code}",
                occurred_at=datetime.combine(payload.sale_date, datetime.min.time(), tzinfo=timezone.utc),
                created_by_user_id=audit_user_id(user),
            )
            db.add(movement)
            db.flush()
            db.add(
                SaleInventoryMovementModel(
                    sale_detail_id=detail.id,
                    inventory_movement_id=movement.id,
                )
            )
            remaining_stock[line.product_resource_id] = stock_for(db, payload.organization_id, line.product_resource_id)

        db.commit()
        db.refresh(sale)
        sale = db.scalar(select(SaleModel).options(selectinload(SaleModel.details)).where(SaleModel.id == sale.id))
        return SaleCreated(sale=sale_to_read(db, sale, include_movements=True), remaining_stock=remaining_stock)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La venta no pudo registrarse por una restriccion de datos. No se desconto stock.",
        ) from exc


@router.get("", response_model=list[SaleRead])
def list_sales(
    organization_id: UUID = Query(...),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    channel_id: UUID | None = Query(default=None),
    point_of_sale_id: UUID | None = Query(default=None),
    product_resource_id: UUID | None = Query(default=None),
    payment_method_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    stmt = (
        select(SaleModel)
        .options(selectinload(SaleModel.details))
        .where(SaleModel.organization_id == organization_id)
    )
    conditions = []
    if date_from:
        conditions.append(SaleModel.sale_date >= date_from)
    if date_to:
        conditions.append(SaleModel.sale_date <= date_to)
    if channel_id:
        conditions.append(SaleModel.channel_id == channel_id)
    if point_of_sale_id:
        conditions.append(SaleModel.point_of_sale_id == point_of_sale_id)
    if payment_method_id:
        conditions.append(SaleModel.payment_method_id == payment_method_id)
    if status_filter and status_filter != "imported":
        try:
            conditions.append(SaleModel.status == SaleStatus(status_filter))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="El estado seleccionado no es valido.") from exc
    if product_resource_id:
        stmt = stmt.join(SaleDetailModel).where(SaleDetailModel.resource_id == product_resource_id)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    system_sales = [
        sale_to_read(db, sale)
        for sale in db.scalars(stmt.order_by(SaleModel.sale_date.desc(), SaleModel.created_at.desc())).unique().all()
    ]

    imported_sales: list[SaleRead] = []
    if not status_filter or status_filter == "imported":
        imported_stmt = select(ImportedSaleModel).where(ImportedSaleModel.organization_id == organization_id)
        if date_from:
            imported_stmt = imported_stmt.where(ImportedSaleModel.sale_date >= date_from)
        if date_to:
            imported_stmt = imported_stmt.where(ImportedSaleModel.sale_date <= date_to)
        if channel_id:
            channel = db.get(SalesChannelModel, channel_id)
            if channel:
                imported_stmt = imported_stmt.where(ImportedSaleModel.channel_name == channel.name)
        if payment_method_id:
            method = db.get(PaymentMethodModel, payment_method_id)
            if method:
                imported_stmt = imported_stmt.where(ImportedSaleModel.payment_method == method.name)
        if product_resource_id:
            product = db.get(ResourceModel, product_resource_id)
            if product:
                imported_stmt = imported_stmt.where(ImportedSaleModel.product_name == product.name)
        if point_of_sale_id:
            imported_stmt = imported_stmt.where(text("1 = 0"))

        imported_sales = [
            imported_sale_to_read(row)
            for row in db.scalars(imported_stmt.order_by(ImportedSaleModel.sale_date.desc())).all()
        ]

    return sorted(system_sales + imported_sales, key=lambda item: item.sale_date, reverse=True)


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(
    sale_id: UUID,
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    sale = db.scalar(
        select(SaleModel)
        .options(selectinload(SaleModel.details))
        .where(SaleModel.id == sale_id, SaleModel.organization_id == organization_id)
    )
    if sale:
        return sale_to_read(db, sale, include_movements=True)

    imported_sale = db.scalar(
        select(ImportedSaleModel).where(
            ImportedSaleModel.id == sale_id,
            ImportedSaleModel.organization_id == organization_id,
        )
    )
    if imported_sale:
        return imported_sale_to_read(imported_sale)

    raise HTTPException(status_code=404, detail="Venta no encontrada.")


@router.post("/{sale_id}/cancel", response_model=SaleRead)
def cancel_sale(
    sale_id: UUID,
    payload: SaleCancel,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    sale = db.scalar(
        select(SaleModel)
        .options(selectinload(SaleModel.details))
        .where(SaleModel.id == sale_id, SaleModel.organization_id == payload.organization_id)
        .with_for_update()
    )
    if sale is None:
        raise HTTPException(status_code=404, detail="Venta no encontrada o importada. Solo se anulan ventas del sistema.")
    if sale.status == SaleStatus.CANCELLED:
        raise HTTPException(status_code=422, detail="Esta venta ya estaba anulada.")

    products = db.scalars(
        select(ResourceModel)
        .where(ResourceModel.id.in_([detail.resource_id for detail in sale.details]))
        .order_by(ResourceModel.id)
        .with_for_update()
    ).all()
    products_by_id = {product.id: product for product in products}

    try:
        for detail in sale.details:
            product = products_by_id[detail.resource_id]
            movement = InventoryMovementModel(
                organization_id=payload.organization_id,
                resource_id=detail.resource_id,
                type=MovementType.SALE_CANCELLATION,
                quantity=detail.quantity,
                unit=product.unit,
                reason=f"Anulacion de venta {sale.code}: {payload.reason}",
                created_by_user_id=audit_user_id(user),
            )
            db.add(movement)
            db.flush()
            db.add(
                SaleInventoryMovementModel(
                    sale_detail_id=detail.id,
                    inventory_movement_id=movement.id,
                )
            )

        sale.status = SaleStatus.CANCELLED
        sale.cancelled_at = datetime.now(timezone.utc)
        sale.cancelled_by_user_id = audit_user_id(user)
        sale.cancellation_reason = payload.reason
        sale.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(sale)
        sale = db.scalar(select(SaleModel).options(selectinload(SaleModel.details)).where(SaleModel.id == sale_id))
        return sale_to_read(db, sale, include_movements=True)
    except Exception:
        db.rollback()
        raise
