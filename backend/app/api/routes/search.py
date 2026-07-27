from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    ExpenseCategoryModel,
    ExpenseModel,
    FormulaModel,
    ImportedExpenseModel,
    ImportedSaleModel,
    PurchaseModel,
    ResourceModel,
    SaleModel,
)
from app.db.session import get_db
from app.schemas.search import SearchResult

router = APIRouter()

RESOURCE_LABELS = {
    "raw_material": "Materia prima",
    "packaging": "Packaging",
    "product": "Producto",
    "mix": "Mezcla",
}


@router.get("", response_model=list[SearchResult])
def global_search(
    organization_id: UUID = Query(...),
    q: str = Query(..., min_length=2),
    limit: int = Query(default=12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    term = f"%{q.strip()}%"
    results: list[SearchResult] = []

    resources = db.scalars(
        select(ResourceModel)
        .where(
            ResourceModel.organization_id == organization_id,
            or_(ResourceModel.name.ilike(term), ResourceModel.code.ilike(term)),
        )
        .order_by(ResourceModel.type, ResourceModel.name)
        .limit(limit)
    ).all()
    resources = sorted(
        resources,
        key=lambda item: (0 if item.type.value == "product" else 1, item.name.lower()),
    )
    for resource in resources:
        results.append(
            SearchResult(
                id=resource.id,
                type="Recurso",
                title=resource.name,
                subtitle=f"{resource.code} - {RESOURCE_LABELS.get(resource.type.value, resource.type.value)}",
                href="/recursos",
            )
        )

    remaining = max(limit - len(results), 0)
    if remaining:
        formulas = db.scalars(
            select(FormulaModel)
            .where(
                FormulaModel.organization_id == organization_id,
                FormulaModel.name.ilike(term),
            )
            .order_by(FormulaModel.name, FormulaModel.version.desc())
            .limit(remaining)
        ).all()
        for formula in formulas:
            results.append(
                SearchResult(
                    id=formula.id,
                    type="Formula",
                    title=f"{formula.name} v{formula.version}",
                    subtitle=f"Estado {formula.status.value}",
                    href="/formulas",
                )
            )

    remaining = max(limit - len(results), 0)
    if remaining:
        purchases = db.scalars(
            select(PurchaseModel)
            .where(
                PurchaseModel.organization_id == organization_id,
                or_(PurchaseModel.code.ilike(term), PurchaseModel.supplier_name.ilike(term)),
            )
            .order_by(PurchaseModel.purchase_date.desc())
            .limit(remaining)
        ).all()
        for purchase in purchases:
            results.append(
                SearchResult(
                    id=purchase.id,
                    type="Compra",
                    title=f"{purchase.code} - {purchase.supplier_name}",
                    subtitle=f"{purchase.purchase_date} - {purchase.status.value}",
                    href="/compras",
                )
            )

    remaining = max(limit - len(results), 0)
    if remaining:
        system_sales = db.scalars(
            select(SaleModel)
            .options(selectinload(SaleModel.details))
            .where(
                SaleModel.organization_id == organization_id,
                or_(SaleModel.code.ilike(term), SaleModel.customer_name.ilike(term)),
            )
            .order_by(SaleModel.sale_date.desc())
            .limit(remaining)
        ).all()
        for sale in system_sales:
            results.append(
                SearchResult(
                    id=sale.id,
                    type="Venta",
                    title=f"{sale.code} - ${sale.total}",
                    subtitle=f"{sale.sale_date} - {sale.status.value}",
                    href="/ventas",
                )
            )

    remaining = max(limit - len(results), 0)
    if remaining:
        imported_sales = db.scalars(
            select(ImportedSaleModel)
            .where(
                ImportedSaleModel.organization_id == organization_id,
                or_(
                    ImportedSaleModel.product_name.ilike(term),
                    ImportedSaleModel.customer_name.ilike(term),
                    ImportedSaleModel.channel_name.ilike(term),
                ),
            )
            .order_by(ImportedSaleModel.sale_date.desc())
            .limit(remaining)
        ).all()
        for sale in imported_sales:
            results.append(
                SearchResult(
                    id=sale.id,
                    type="Venta historica",
                    title=sale.product_name,
                    subtitle=f"{sale.sale_date} - {sale.channel_name or 'Sin canal'}",
                    href="/ventas",
                )
            )

    remaining = max(limit - len(results), 0)
    if remaining:
        expenses = db.scalars(
            select(ExpenseModel)
            .where(
                ExpenseModel.organization_id == organization_id,
                or_(
                    ExpenseModel.description.ilike(term),
                    ExpenseModel.supplier_name.ilike(term),
                    ExpenseModel.receipt_number.ilike(term),
                    ExpenseModel.notes.ilike(term),
                ),
            )
            .order_by(ExpenseModel.expense_date.desc())
            .limit(remaining)
        ).all()
        for expense in expenses:
            category = db.get(ExpenseCategoryModel, expense.category_id)
            results.append(
                SearchResult(
                    id=expense.id,
                    type="Gasto",
                    title=f"{expense.description} - ${expense.amount}",
                    subtitle=f"{expense.expense_date} - {category.name if category else 'Sin categoria'} - {expense.status}",
                    href=f"/gastos/{expense.id}",
                )
            )

    remaining = max(limit - len(results), 0)
    if remaining:
        imported_expenses = db.scalars(
            select(ImportedExpenseModel)
            .where(
                ImportedExpenseModel.organization_id == organization_id,
                or_(
                    ImportedExpenseModel.category_name.ilike(term),
                    ImportedExpenseModel.supplier_name.ilike(term),
                    ImportedExpenseModel.payment_method.ilike(term),
                ),
            )
            .order_by(ImportedExpenseModel.expense_date.desc())
            .limit(remaining)
        ).all()
        for expense in imported_expenses:
            results.append(
                SearchResult(
                    id=expense.id,
                    type="Gasto historico",
                    title=f"{expense.category_name} - ${expense.amount}",
                    subtitle=f"{expense.expense_date} - {expense.payment_method or 'Sin medio'}",
                    href=f"/gastos/{expense.id}?origin=imported",
                )
            )

    return results
