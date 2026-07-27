from __future__ import annotations

import json
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/eter_erp"
MIGRATION_FILE = Path("database/migrations/001_resource_costs_product_prices.sql")
MIGRATION_FILES = [
    Path("database/migrations/001_resource_costs_product_prices.sql"),
    Path("database/migrations/002_imported_sales_expenses_and_non_negative.sql"),
]


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def strip_accents(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def next_code(existing_codes: set[str], resource_type: str) -> str:
    prefix = {
        "raw_material": "MP",
        "packaging": "PK",
        "product": "PR",
        "mix": "MX",
    }[resource_type]
    max_number = 0
    for code in existing_codes:
        match = re.match(rf"^{prefix}-(\d+)$", code, flags=re.IGNORECASE)
        if match:
            max_number = max(max_number, int(match.group(1)))
    while True:
        max_number += 1
        code = f"{prefix}-{max_number:04d}"
        if code not in existing_codes:
            existing_codes.add(code)
            return code


def decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def load_existing_resources(conn: psycopg.Connection) -> tuple[dict[str, dict], set[str]]:
    rows = conn.execute(
        """
        select id, code, name, type
        from resources
        where organization_id = %s
        """,
        (ORGANIZATION_ID,),
    ).fetchall()
    by_name = {normalize_name(row["name"]): row for row in rows}
    codes = {row["code"] for row in rows}
    return by_name, codes


def main() -> None:
    payload = json.load(sys.stdin)
    summary = {
        "resources_created": 0,
        "resources_matched": 0,
        "resource_costs_inserted": 0,
        "product_prices_inserted": 0,
        "formulas_inserted": 0,
        "formulas_updated": 0,
        "formula_items_inserted": 0,
        "sales_channels_inserted": 0,
        "expense_categories_inserted": 0,
        "imported_sales_inserted": 0,
        "imported_expenses_inserted": 0,
        "names_normalized": 0,
    }

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        for migration_file in MIGRATION_FILES:
            if migration_file.exists():
                conn.execute(migration_file.read_text(encoding="utf-8"))

        for table, column in [
            ("resources", "name"),
            ("formulas", "name"),
            ("resource_costs", "supplier_name"),
            ("imported_sales", "customer_name"),
            ("imported_sales", "department"),
            ("imported_sales", "channel_name"),
            ("imported_sales", "product_name"),
            ("imported_expenses", "category_name"),
            ("imported_expenses", "supplier_name"),
            ("sales_channels", "name"),
            ("expense_categories", "name"),
        ]:
            rows = conn.execute(f"select id, {column} from {table} where {column} is not null").fetchall()
            for row in rows:
                clean_value = strip_accents(row[column])
                if clean_value != row[column]:
                    conn.execute(f"update {table} set {column} = %s where id = %s", (clean_value, row["id"]))
                    summary["names_normalized"] += 1

        existing_by_name, existing_codes = load_existing_resources(conn)

        for resource in payload["resources"]:
            normalized_name = resource["normalized_name"]
            if normalized_name in existing_by_name:
                summary["resources_matched"] += 1
                continue

            code = next_code(existing_codes, resource["type"])
            row = conn.execute(
                """
                insert into resources (organization_id, code, name, type, unit, minimum_stock)
                values (%s, %s, %s, %s, %s, 0)
                returning id, code, name, type
                """,
                (
                    ORGANIZATION_ID,
                    code,
                    strip_accents(resource["name"]),
                    resource["type"],
                    resource["unit"],
                ),
            ).fetchone()
            existing_by_name[normalized_name] = row
            summary["resources_created"] += 1

        for cost in payload["resource_costs"]:
            resource = existing_by_name.get(cost["normalized_name"])
            if not resource:
                continue
            result = conn.execute(
                """
                insert into resource_costs (
                  organization_id,
                  resource_id,
                  amount,
                  unit,
                  supplier_name,
                  effective_date,
                  source,
                  notes
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict do nothing
                """,
                (
                    ORGANIZATION_ID,
                    resource["id"],
                    Decimal(str(cost["amount"])),
                    cost["unit"],
                    strip_accents(cost.get("supplier_name")),
                    cost.get("effective_date"),
                    cost["source"],
                    cost.get("notes"),
                ),
            )
            summary["resource_costs_inserted"] += max(0, result.rowcount)

        for price in payload["product_prices"]:
            product = existing_by_name.get(price["normalized_name"])
            if not product:
                continue
            result = conn.execute(
                """
                insert into product_prices (
                  organization_id,
                  product_resource_id,
                  price_list_name,
                  sale_price,
                  variable_cost_snapshot,
                  contribution_margin,
                  contribution_margin_pct,
                  effective_date,
                  source
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict do nothing
                """,
                (
                    ORGANIZATION_ID,
                    product["id"],
                    price["price_list_name"],
                    Decimal(str(price["sale_price"])),
                    decimal_or_none(price.get("variable_cost_snapshot")),
                    decimal_or_none(price.get("contribution_margin")),
                    decimal_or_none(price.get("contribution_margin_pct")),
                    price.get("effective_date"),
                    price["source"],
                ),
            )
            summary["product_prices_inserted"] += max(0, result.rowcount)

        for formula in payload.get("formulas", []):
            product = existing_by_name.get(formula["normalized_name"])
            existing_formulas = conn.execute(
                """
                select id, name
                from formulas
                where organization_id = %s
                  and version = %s
                """,
                (ORGANIZATION_ID, formula["version"]),
            ).fetchall()
            formula_row = next(
                (row for row in existing_formulas if normalize_name(row["name"]) == formula["normalized_name"]),
                None,
            )

            if formula_row:
                conn.execute(
                    """
                    update formulas
                    set product_resource_id = %s,
                        name = %s,
                        status = %s,
                        active_version = %s,
                        notes = %s,
                        updated_at = now()
                    where id = %s
                    """,
                    (
                        product["id"] if product else None,
                        strip_accents(formula["name"]),
                        formula["status"],
                        formula["active_version"],
                        formula.get("notes"),
                        formula_row["id"],
                    ),
                )
                conn.execute("delete from formula_items where formula_id = %s", (formula_row["id"],))
                summary["formulas_updated"] += 1
            else:
                formula_row = conn.execute(
                    """
                    insert into formulas (
                      organization_id,
                      product_resource_id,
                      name,
                      version,
                      status,
                      active_version,
                      notes
                    )
                    values (%s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        ORGANIZATION_ID,
                        product["id"] if product else None,
                        strip_accents(formula["name"]),
                        formula["version"],
                        formula["status"],
                        formula["active_version"],
                        formula.get("notes"),
                    ),
                ).fetchone()
                summary["formulas_inserted"] += 1

            for item in formula["items"]:
                ingredient = existing_by_name.get(item["normalized_name"])
                if not ingredient:
                    continue
                result = conn.execute(
                    """
                    insert into formula_items (
                      formula_id,
                      ingredient_resource_id,
                      percentage,
                      sort_order
                    )
                    values (%s, %s, %s, %s)
                    on conflict do nothing
                    """,
                    (
                        formula_row["id"],
                        ingredient["id"],
                        Decimal(str(item["percentage"])),
                        item["sort_order"],
                    ),
                )
                summary["formula_items_inserted"] += max(0, result.rowcount)

        for channel_name in payload.get("sales_channels", []):
            result = conn.execute(
                """
                insert into sales_channels (organization_id, name, source)
                values (%s, %s, %s)
                on conflict do nothing
                """,
                (ORGANIZATION_ID, strip_accents(channel_name), "gestion diaria mensual anual.xlsx / Datos"),
            )
            summary["sales_channels_inserted"] += max(0, result.rowcount)

        for category_name in payload.get("expense_categories", []):
            result = conn.execute(
                """
                insert into expense_categories (organization_id, name, source)
                values (%s, %s, %s)
                on conflict do nothing
                """,
                (ORGANIZATION_ID, strip_accents(category_name), "gestion diaria mensual anual.xlsx / Datos"),
            )
            summary["expense_categories_inserted"] += max(0, result.rowcount)

        for sale in payload.get("imported_sales", []):
            result = conn.execute(
                """
                insert into imported_sales (
                  organization_id,
                  sale_date,
                  customer_name,
                  department,
                  channel_name,
                  product_name,
                  quantity,
                  unit_price,
                  total_amount,
                  payment_method,
                  source_sheet,
                  source_row,
                  control_status
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict do nothing
                """,
                (
                    ORGANIZATION_ID,
                    sale["sale_date"],
                    strip_accents(sale.get("customer_name")),
                    strip_accents(sale.get("department")),
                    strip_accents(sale.get("channel_name")),
                    strip_accents(sale["product_name"]),
                    Decimal(str(sale["quantity"])),
                    decimal_or_none(sale.get("unit_price")),
                    decimal_or_none(sale.get("total_amount")),
                    strip_accents(sale.get("payment_method")),
                    sale["source_sheet"],
                    sale["source_row"],
                    strip_accents(sale.get("control_status")),
                ),
            )
            summary["imported_sales_inserted"] += max(0, result.rowcount)

        for expense in payload.get("imported_expenses", []):
            result = conn.execute(
                """
                insert into imported_expenses (
                  organization_id,
                  expense_date,
                  category_name,
                  supplier_name,
                  amount,
                  payment_method,
                  source_sheet,
                  source_row,
                  control_status
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                on conflict do nothing
                """,
                (
                    ORGANIZATION_ID,
                    expense["expense_date"],
                    strip_accents(expense["category_name"]),
                    strip_accents(expense.get("supplier_name")),
                    Decimal(str(expense["amount"])),
                    strip_accents(expense.get("payment_method")),
                    expense["source_sheet"],
                    expense["source_row"],
                    strip_accents(expense.get("control_status")),
                ),
            )
            summary["imported_expenses_inserted"] += max(0, result.rowcount)

        conn.commit()

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
