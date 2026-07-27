from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.dashboard import DashboardActivityItem, DashboardSummary

router = APIRouter()


def scalar_int(db: Session, sql: str, organization_id: UUID) -> int:
    return int(db.execute(text(sql), {"organization_id": organization_id}).scalar() or 0)


def scalar_decimal(db: Session, sql: str, organization_id: UUID) -> Decimal:
    return Decimal(str(db.execute(text(sql), {"organization_id": organization_id}).scalar() or 0))


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    expense_row = db.execute(
        text(
            """
            with all_expenses as (
              select e.expense_date, c.name as category_name, e.amount
              from expenses e
              join expense_categories c on c.id = e.category_id
              where e.organization_id = :organization_id
                and e.status = 'confirmed'
              union all
              select expense_date, category_name, amount
              from imported_expenses
              where organization_id = :organization_id
            ),
            year_expenses as (
              select * from all_expenses
              where expense_date between :year_start and :today
            ),
            top_category as (
              select category_name, sum(amount) as total
              from year_expenses
              group by category_name
              order by total desc
              limit 1
            )
            select
              coalesce((select sum(amount) from all_expenses where expense_date between :month_start and :today), 0) as month_total,
              coalesce((select sum(amount) from all_expenses where expense_date between :year_start and :today), 0) as year_total,
              coalesce((select count(*) from year_expenses), 0) as count,
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
        {
            "organization_id": organization_id,
            "month_start": month_start,
            "year_start": year_start,
            "today": today,
        },
    ).mappings().one()

    return DashboardSummary(
        resources_count=scalar_int(
            db,
            "select count(*) from resources where organization_id = :organization_id and active = true",
            organization_id,
        ),
        formulas_count=scalar_int(
            db,
            "select count(*) from formulas where organization_id = :organization_id",
            organization_id,
        ),
        production_batches_count=scalar_int(
            db,
            "select count(*) from production_batches where organization_id = :organization_id",
            organization_id,
        ),
        low_stock_count=scalar_int(
            db,
            """
            select count(*)
            from resources r
            left join current_stock s
              on s.resource_id = r.id
             and s.organization_id = r.organization_id
            where r.organization_id = :organization_id
              and r.active = true
              and r.minimum_stock > 0
              and coalesce(s.quantity, 0) <= r.minimum_stock
            """,
            organization_id,
        ),
        imported_sales_count=scalar_int(
            db,
            "select count(*) from imported_sales where organization_id = :organization_id",
            organization_id,
        ),
        imported_sales_total=scalar_decimal(
            db,
            "select coalesce(sum(total_amount), 0) from imported_sales where organization_id = :organization_id",
            organization_id,
        ),
        imported_expenses_count=scalar_int(
            db,
            "select count(*) from imported_expenses where organization_id = :organization_id",
            organization_id,
        ),
        imported_expenses_total=scalar_decimal(
            db,
            "select coalesce(sum(amount), 0) from imported_expenses where organization_id = :organization_id",
            organization_id,
        ),
        sales_channels_count=scalar_int(
            db,
            "select count(*) from sales_channels where organization_id = :organization_id",
            organization_id,
        ),
        expense_categories_count=scalar_int(
            db,
            "select count(*) from expense_categories where organization_id = :organization_id",
            organization_id,
        ),
        system_sales_count=scalar_int(
            db,
            """
            select count(*)
            from sales
            where organization_id = :organization_id
              and source = 'system'
              and status = 'confirmed'
            """,
            organization_id,
        ),
        system_sales_total=scalar_decimal(
            db,
            """
            select coalesce(sum(total), 0)
            from sales
            where organization_id = :organization_id
              and source = 'system'
              and status = 'confirmed'
            """,
            organization_id,
        ),
        cancelled_system_sales_count=scalar_int(
            db,
            """
            select count(*)
            from sales
            where organization_id = :organization_id
              and source = 'system'
              and status = 'cancelled'
            """,
            organization_id,
        ),
        system_expenses_count=scalar_int(
            db,
            "select count(*) from expenses where organization_id = :organization_id and status = 'confirmed'",
            organization_id,
        ),
        system_expenses_total=scalar_decimal(
            db,
            "select coalesce(sum(amount), 0) from expenses where organization_id = :organization_id and status = 'confirmed'",
            organization_id,
        ),
        cancelled_system_expenses_count=scalar_int(
            db,
            "select count(*) from expenses where organization_id = :organization_id and status = 'cancelled'",
            organization_id,
        ),
        month_expenses_total=expense_row["month_total"],
        year_expenses_total=expense_row["year_total"],
        expenses_count=expense_row["count"],
        top_expense_category_name=expense_row["top_category_name"],
        top_expense_category_total=expense_row["top_category_total"],
        sales_same_period_total=expense_row["sales_same_period_total"],
        confirmed_purchases_count=scalar_int(
            db,
            "select count(*) from purchases where organization_id = :organization_id and status = 'confirmed'",
            organization_id,
        ),
        confirmed_purchases_total=scalar_decimal(
            db,
            "select coalesce(sum(total), 0) from purchases where organization_id = :organization_id and status = 'confirmed'",
            organization_id,
        ),
        draft_purchases_count=scalar_int(
            db,
            "select count(*) from purchases where organization_id = :organization_id and status = 'draft'",
            organization_id,
        ),
        cancelled_purchases_count=scalar_int(
            db,
            "select count(*) from purchases where organization_id = :organization_id and status = 'cancelled'",
            organization_id,
        ),
        finished_products_stock_total=scalar_decimal(
            db,
            """
            select coalesce(sum(s.quantity), 0)
            from resources r
            join current_stock s
              on s.resource_id = r.id
             and s.organization_id = r.organization_id
            where r.organization_id = :organization_id
              and r.active = true
              and r.type = 'product'
            """,
            organization_id,
        ),
    )


@router.get("/activity", response_model=list[DashboardActivityItem])
def dashboard_activity(
    organization_id: UUID = Query(...),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            """
            select id::text,
                   sale_date::text as date,
                   'Venta' as type,
                   code || ' - ' || coalesce(customer_name, 'Venta sin cliente') as description,
                   ('$ ' || trim(to_char(total, 'FM999999999990D00'))) as value,
                   '/ventas' as href,
                   created_at
            from sales
            where organization_id = :organization_id
            union all
            select id::text,
                   expense_date::text as date,
                   case when status = 'cancelled' then 'Gasto anulado' else 'Gasto' end as type,
                   description as description,
                   ('$ ' || trim(to_char(amount, 'FM999999999990D00'))) as value,
                   '/gastos/' || id::text as href,
                   created_at
            from expenses
            where organization_id = :organization_id
            union all
            select id::text,
                   purchase_date::text as date,
                   case when status = 'cancelled' then 'Compra anulada' else 'Compra' end as type,
                   code || ' - ' || supplier_name as description,
                   ('$ ' || trim(to_char(total, 'FM999999999990D00'))) as value,
                   '/compras' as href,
                   created_at
            from purchases
            where organization_id = :organization_id
            union all
            select id::text,
                   elaboration_date::text as date,
                   'Produccion' as type,
                   batch_number || ' - lote registrado' as description,
                   trim(to_char(target_weight, 'FM999999999990D000')) || ' ' || unit as value,
                   '/produccion' as href,
                   created_at
            from production_batches
            where organization_id = :organization_id
            order by created_at desc
            limit 5
            """
        ),
        {"organization_id": organization_id},
    ).mappings()
    return [DashboardActivityItem(**row) for row in rows]
