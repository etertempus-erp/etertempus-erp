from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/eter_erp"


def database_url() -> str:
    url = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    return url.replace("postgresql+psycopg://", "postgresql://")


def has_column(conn: psycopg.Connection, table: str, column: str) -> bool:
    row = conn.execute(
        """
        select 1
        from information_schema.columns
        where table_schema = 'public'
          and table_name = %s
          and column_name = %s
        """,
        (table, column),
    ).fetchone()
    return row is not None


def main() -> None:
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        has_purchase_id = has_column(conn, "resource_costs", "purchase_id")
        has_active = has_column(conn, "resource_costs", "active")

        purchase_join = (
            "left join purchases p on p.id = rc.purchase_id"
            if has_purchase_id
            else "left join purchases p on p.organization_id = rc.organization_id and rc.notes = ('Compra ' || p.code)"
        )
        replacement_purchase_join = (
            "left join purchases p2 on p2.id = rc.purchase_id"
            if has_purchase_id
            else "left join purchases p2 on p2.organization_id = rc.organization_id and rc.notes = ('Compra ' || p2.code)"
        )
        active_filter = "and coalesce(rc.active, true) = true" if has_active else ""

        rows = conn.execute(
            f"""
            with ranked_costs as (
              select
                rc.id,
                rc.organization_id,
                rc.resource_id,
                rc.amount,
                rc.unit,
                rc.supplier_name,
                rc.effective_date,
                rc.source,
                rc.notes,
                p.code as purchase_code,
                p.status as purchase_status,
                row_number() over (
                  partition by rc.organization_id, rc.resource_id
                  order by rc.effective_date desc nulls last, rc.created_at desc
                ) as rn
              from resource_costs rc
              {purchase_join}
            )
            select
              r.code as resource_code,
              r.name as resource_name,
              latest.amount as incorrect_amount,
              latest.unit as incorrect_unit,
              latest.supplier_name as incorrect_supplier,
              latest.purchase_code as cancelled_purchase,
              replacement.amount as replacement_amount,
              replacement.unit as replacement_unit,
              replacement.supplier_name as replacement_supplier,
              replacement.source as replacement_source,
              replacement.effective_date as replacement_date
            from ranked_costs latest
            join resources r on r.id = latest.resource_id
            left join lateral (
              select rc.amount, rc.unit, rc.supplier_name, rc.source, rc.effective_date
              from resource_costs rc
              {replacement_purchase_join}
              where rc.organization_id = latest.organization_id
                and rc.resource_id = latest.resource_id
                and rc.id <> latest.id
                and not (rc.source = 'purchase' and p2.status = 'cancelled')
                {active_filter}
              order by rc.effective_date desc nulls last, rc.created_at desc
              limit 1
            ) replacement on true
            where latest.rn = 1
              and latest.source = 'purchase'
              and latest.purchase_status = 'cancelled'
            order by r.name;
            """
        ).fetchall()

    if not rows:
        print("No se encontraron recursos cuyo ultimo costo provenga de una compra anulada.")
        return

    print("Recursos con costo activo sospechoso por compra anulada:")
    for row in rows:
        replacement = (
            f"{row['replacement_amount']} {row['replacement_unit']} ({row['replacement_source']}, {row['replacement_date']})"
            if row["replacement_amount"] is not None
            else "sin costo valido anterior"
        )
        print(
            "- "
            f"{row['resource_code']} | {row['resource_name']} | "
            f"costo incorrecto: {row['incorrect_amount']} {row['incorrect_unit']} | "
            f"compra anulada: {row['cancelled_purchase']} | "
            f"reemplazo sugerido: {replacement}"
        )


if __name__ == "__main__":
    main()
