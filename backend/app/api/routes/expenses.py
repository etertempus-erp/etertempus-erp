from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    ExpenseCategoryModel,
    ExpenseModel,
    ImportedExpenseModel,
    PaymentMethodModel,
)
from app.db.session import get_db
from app.schemas.expenses import (
    ExpenseCancel,
    ExpenseCreate,
    ExpenseListResponse,
    ExpenseOption,
    ExpenseOptions,
    ExpenseRead,
    ExpenseSummary,
    ExpenseUpdate,
)

router = APIRouter()
MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def expense_to_read(db: Session, expense: ExpenseModel) -> ExpenseRead:
    category = db.get(ExpenseCategoryModel, expense.category_id)
    payment = db.get(PaymentMethodModel, expense.payment_method_id)
    return ExpenseRead(
        id=expense.id,
        expense_date=expense.expense_date,
        category_id=expense.category_id,
        category_name=category.name if category else "Categoria no encontrada",
        description=expense.description,
        amount=expense.amount,
        payment_method_id=expense.payment_method_id,
        payment_method_name=payment.name if payment else None,
        supplier_name=expense.supplier_name,
        receipt_number=expense.receipt_number,
        notes=expense.notes,
        status=expense.status,
        origin=expense.origin,
        source_label="ERP",
        cancelled_at=expense.cancelled_at,
        cancellation_reason=expense.cancellation_reason,
        editable=expense.status == "confirmed",
        cancellable=expense.status == "confirmed",
    )


def imported_expense_to_read(expense: ImportedExpenseModel) -> ExpenseRead:
    return ExpenseRead(
        id=expense.id,
        expense_date=expense.expense_date,
        category_name=expense.category_name,
        description=expense.category_name,
        amount=expense.amount,
        payment_method_name=expense.payment_method,
        supplier_name=expense.supplier_name,
        status="confirmed",
        origin="imported",
        source_label=f"{expense.source_sheet}, fila {expense.source_row}",
        notes=expense.control_status,
        editable=False,
        cancellable=False,
    )


def validate_category_and_payment(
    db: Session,
    organization_id: UUID,
    category_id: UUID,
    payment_method_id: UUID,
) -> None:
    category = db.get(ExpenseCategoryModel, category_id)
    if category is None or category.organization_id != organization_id:
        raise HTTPException(status_code=422, detail="Selecciona una categoria valida.")

    payment = db.get(PaymentMethodModel, payment_method_id)
    if payment is None or payment.organization_id != organization_id or not payment.active:
        raise HTTPException(status_code=422, detail="Selecciona un medio de pago valido.")


@router.get("/options", response_model=ExpenseOptions)
def expense_options(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    categories = db.scalars(
        select(ExpenseCategoryModel)
        .where(ExpenseCategoryModel.organization_id == organization_id)
        .order_by(ExpenseCategoryModel.name)
    ).all()
    payment_methods = db.scalars(
        select(PaymentMethodModel)
        .where(PaymentMethodModel.organization_id == organization_id, PaymentMethodModel.active.is_(True))
        .order_by(PaymentMethodModel.name)
    ).all()
    supplier_rows = db.execute(
        text(
            """
            select distinct supplier_name
            from (
              select supplier_name from expenses where organization_id = :organization_id and supplier_name is not null
              union all
              select supplier_name from imported_expenses where organization_id = :organization_id and supplier_name is not null
            ) suppliers
            where trim(supplier_name) <> ''
            order by supplier_name
            """
        ),
        {"organization_id": organization_id},
    ).scalars()
    return ExpenseOptions(
        categories=[ExpenseOption(id=item.id, name=item.name) for item in categories],
        payment_methods=[ExpenseOption(id=item.id, name=item.name) for item in payment_methods],
        suppliers=list(supplier_rows),
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ExpenseRead)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)):
    try:
        validate_category_and_payment(db, payload.organization_id, payload.category_id, payload.payment_method_id)
        expense = ExpenseModel(
            organization_id=payload.organization_id,
            expense_date=payload.expense_date,
            category_id=payload.category_id,
            description=payload.description.strip(),
            amount=money(payload.amount),
            payment_method_id=payload.payment_method_id,
            supplier_name=payload.supplier_name.strip() if payload.supplier_name else None,
            receipt_number=payload.receipt_number.strip() if payload.receipt_number else None,
            notes=payload.notes,
            status="confirmed",
            origin="system",
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense_to_read(db, expense)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo guardar el gasto.") from exc


@router.get("", response_model=ExpenseListResponse)
def list_expenses(
    organization_id: UUID = Query(...),
    date_from: date | None = None,
    date_to: date | None = None,
    category_id: UUID | None = None,
    payment_method_id: UUID | None = None,
    supplier: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    origin: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    if status_filter and status_filter not in {"confirmed", "cancelled"}:
        raise HTTPException(status_code=422, detail="El estado seleccionado no es valido.")
    if origin and origin not in {"system", "imported"}:
        raise HTTPException(status_code=422, detail="El origen seleccionado no es valido.")

    system_stmt = (
        select(ExpenseModel)
        .where(ExpenseModel.organization_id == organization_id)
        .order_by(ExpenseModel.expense_date.desc(), ExpenseModel.created_at.desc())
    )
    imported_stmt = (
        select(ImportedExpenseModel)
        .where(ImportedExpenseModel.organization_id == organization_id)
        .order_by(ImportedExpenseModel.expense_date.desc(), ImportedExpenseModel.created_at.desc())
    )

    if date_from:
        system_stmt = system_stmt.where(ExpenseModel.expense_date >= date_from)
        imported_stmt = imported_stmt.where(ImportedExpenseModel.expense_date >= date_from)
    if date_to:
        system_stmt = system_stmt.where(ExpenseModel.expense_date <= date_to)
        imported_stmt = imported_stmt.where(ImportedExpenseModel.expense_date <= date_to)
    if category_id:
        category = db.get(ExpenseCategoryModel, category_id)
        if category is None or category.organization_id != organization_id:
            raise HTTPException(status_code=422, detail="Selecciona una categoria valida.")
        system_stmt = system_stmt.where(ExpenseModel.category_id == category_id)
        imported_stmt = imported_stmt.where(func.lower(ImportedExpenseModel.category_name) == category.name.lower())
    if payment_method_id:
        payment = db.get(PaymentMethodModel, payment_method_id)
        if payment is None or payment.organization_id != organization_id:
            raise HTTPException(status_code=422, detail="Selecciona un medio de pago valido.")
        system_stmt = system_stmt.where(ExpenseModel.payment_method_id == payment_method_id)
        imported_stmt = imported_stmt.where(func.lower(ImportedExpenseModel.payment_method) == payment.name.lower())
    if supplier:
        like = f"%{supplier.strip()}%"
        system_stmt = system_stmt.where(ExpenseModel.supplier_name.ilike(like))
        imported_stmt = imported_stmt.where(ImportedExpenseModel.supplier_name.ilike(like))
    if q:
        like = f"%{q.strip()}%"
        system_stmt = system_stmt.where(
            or_(ExpenseModel.description.ilike(like), ExpenseModel.notes.ilike(like), ExpenseModel.supplier_name.ilike(like))
        )
        imported_stmt = imported_stmt.where(
            or_(ImportedExpenseModel.category_name.ilike(like), ImportedExpenseModel.supplier_name.ilike(like))
        )
    if status_filter:
        system_stmt = system_stmt.where(ExpenseModel.status == status_filter)
        if status_filter == "cancelled":
            imported_stmt = imported_stmt.where(text("1 = 0"))
    if origin == "system":
        imported_stmt = imported_stmt.where(text("1 = 0"))
    if origin == "imported":
        system_stmt = system_stmt.where(text("1 = 0"))

    items = [expense_to_read(db, row) for row in db.scalars(system_stmt).all()]
    items.extend(imported_expense_to_read(row) for row in db.scalars(imported_stmt).all())
    items.sort(key=lambda item: item.expense_date, reverse=True)
    total = money(sum((item.amount for item in items if item.status == "confirmed"), Decimal("0")))
    return ExpenseListResponse(items=items, total=total, count=len(items))


@router.get("/summary", response_model=ExpenseSummary)
def expense_summary(
    organization_id: UUID = Query(...),
    reference_date: date | None = None,
    db: Session = Depends(get_db),
):
    today = reference_date or date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    params = {"organization_id": organization_id, "month_start": month_start, "year_start": year_start, "today": today}

    row = db.execute(
        text(
            """
            with all_expenses as (
              select expense_date, category_id::text as category_key, c.name as category_name, amount
              from expenses e
              join expense_categories c on c.id = e.category_id
              where e.organization_id = :organization_id and e.status = 'confirmed'
              union all
              select expense_date, lower(category_name) as category_key, category_name, amount
              from imported_expenses
              where organization_id = :organization_id
            ),
            period_expenses as (
              select * from all_expenses where expense_date between :year_start and :today
            ),
            top_category as (
              select category_name, sum(amount) as total
              from period_expenses
              group by category_name
              order by total desc
              limit 1
            )
            select
              coalesce((select sum(amount) from all_expenses where expense_date between :month_start and :today), 0) as month_total,
              coalesce((select sum(amount) from all_expenses where expense_date between :year_start and :today), 0) as year_total,
              coalesce((select count(*) from all_expenses where expense_date between :year_start and :today), 0) as count,
              (select category_name from top_category) as top_category_name,
              coalesce((select total from top_category), 0) as top_category_total,
              (
                select coalesce(sum(total), 0)
                from sales
                where organization_id = :organization_id
                  and source = 'system'
                  and status = 'confirmed'
                  and sale_date between :year_start and :today
              ) + (
                select coalesce(sum(total_amount), 0)
                from imported_sales
                where organization_id = :organization_id
                  and sale_date between :year_start and :today
              ) as sales_same_period_total
            """
        ),
        params,
    ).mappings().one()
    return ExpenseSummary(**row)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: UUID,
    organization_id: UUID = Query(...),
    origin: str | None = None,
    db: Session = Depends(get_db),
):
    if origin != "imported":
        expense = db.get(ExpenseModel, expense_id)
        if expense and expense.organization_id == organization_id:
            return expense_to_read(db, expense)
    imported = db.get(ImportedExpenseModel, expense_id)
    if imported and imported.organization_id == organization_id:
        return imported_expense_to_read(imported)
    raise HTTPException(status_code=404, detail="Gasto no encontrado.")


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(expense_id: UUID, payload: ExpenseUpdate, db: Session = Depends(get_db)):
    expense = db.get(ExpenseModel, expense_id)
    if expense is None or expense.organization_id != payload.organization_id:
        raise HTTPException(status_code=404, detail="Gasto no encontrado.")
    if expense.status == "cancelled":
        raise HTTPException(status_code=422, detail="No se puede editar un gasto anulado.")

    expense.supplier_name = payload.supplier_name.strip() if payload.supplier_name else None
    expense.receipt_number = payload.receipt_number.strip() if payload.receipt_number else None
    expense.notes = payload.notes
    expense.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(expense)
    return expense_to_read(db, expense)


@router.post("/{expense_id}/cancel", response_model=ExpenseRead)
def cancel_expense(expense_id: UUID, payload: ExpenseCancel, db: Session = Depends(get_db)):
    expense = db.get(ExpenseModel, expense_id)
    if expense is None or expense.organization_id != payload.organization_id:
        raise HTTPException(status_code=404, detail="Gasto no encontrado o importado. Solo se anulan gastos del ERP.")
    if expense.status == "cancelled":
        raise HTTPException(status_code=422, detail="Este gasto ya estaba anulado.")

    expense.status = "cancelled"
    expense.cancelled_at = datetime.now(timezone.utc)
    expense.cancellation_reason = payload.reason.strip()
    expense.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(expense)
    return expense_to_read(db, expense)
