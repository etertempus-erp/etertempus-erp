from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP

import psycopg
from psycopg.rows import dict_row


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/eter_erp"


def database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).replace("postgresql+psycopg://", "postgresql://")

MERGES = {
    "T? Verde": "Te Verde",
    "T? Wulong /Oolong": "Te Wulong /Oolong",
    "T? Hei Cha / Dark Tea": "Te Hei Cha / Dark Tea",
    "T? Blanco": "Te Blanco",
    "P?talos de Calendula": "Petalos de Calendula",
}

RENAME = {
    "Te negro": "Te Negro",
    "lavanda": "Lavanda",
    "hibisco": "Hibisco",
    "Jengibre Desidratado": "Jengibre Deshidratado",
}


def merge_resource(conn: psycopg.Connection, bad_name: str, good_name: str) -> bool:
    bad = conn.execute(
        "select id from resources where name = %s and type = 'raw_material'",
        (bad_name,),
    ).fetchone()
    good = conn.execute(
        "select id from resources where name = %s and type = 'raw_material'",
        (good_name,),
    ).fetchone()
    if not bad or not good:
        return False

    bad_id = bad["id"]
    good_id = good["id"]
    conn.execute(
        """
        delete from resource_costs bad_cost
        where bad_cost.resource_id = %s
          and exists (
            select 1
            from resource_costs good_cost
            where good_cost.resource_id = %s
              and good_cost.organization_id = bad_cost.organization_id
              and good_cost.amount = bad_cost.amount
              and good_cost.unit = bad_cost.unit
              and coalesce(good_cost.supplier_name, '') = coalesce(bad_cost.supplier_name, '')
              and coalesce(good_cost.effective_date, '1900-01-01'::date) =
                  coalesce(bad_cost.effective_date, '1900-01-01'::date)
              and good_cost.source = bad_cost.source
          )
        """,
        (bad_id, good_id),
    )
    conn.execute("update inventory_movements set resource_id = %s where resource_id = %s", (good_id, bad_id))
    conn.execute("update resource_costs set resource_id = %s where resource_id = %s", (good_id, bad_id))
    conn.execute(
        """
        update formula_items
        set ingredient_resource_id = %s
        where ingredient_resource_id = %s
          and not exists (
            select 1
            from formula_items existing
            where existing.formula_id = formula_items.formula_id
              and existing.ingredient_resource_id = %s
          )
        """,
        (good_id, bad_id, good_id),
    )
    conn.execute("delete from formula_items where ingredient_resource_id = %s", (bad_id,))
    conn.execute("delete from resources where id = %s", (bad_id,))
    return True


def round_formula_percentages(conn: psycopg.Connection) -> int:
    changed = 0
    formula_rows = conn.execute("select id from formulas order by name, version").fetchall()
    for formula in formula_rows:
        items = conn.execute(
            """
            select id, percentage
            from formula_items
            where formula_id = %s
            order by sort_order, id
            """,
            (formula["id"],),
        ).fetchall()
        if not items:
            continue

        running_total = Decimal("0.00")
        rounded_items: list[tuple[object, Decimal]] = []
        for index, item in enumerate(items):
            if index == len(items) - 1:
                rounded = Decimal("100.00") - running_total
            else:
                rounded = Decimal(item["percentage"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                running_total += rounded
            rounded_items.append((item["id"], rounded))

        for item_id, rounded in rounded_items:
            result = conn.execute(
                "update formula_items set percentage = %s where id = %s and percentage <> %s",
                (rounded, item_id, rounded),
            )
            changed += max(0, result.rowcount)
    return changed


def main() -> None:
    summary = {
        "resources_merged": 0,
        "resources_renamed": 0,
        "formula_items_rounded": 0,
    }
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        for bad_name, good_name in MERGES.items():
            if merge_resource(conn, bad_name, good_name):
                summary["resources_merged"] += 1

        for old_name, new_name in RENAME.items():
            result = conn.execute(
                "update resources set name = %s where name = %s",
                (new_name, old_name),
            )
            summary["resources_renamed"] += max(0, result.rowcount)

        summary["formula_items_rounded"] = round_formula_percentages(conn)
        conn.commit()

    print(summary)


if __name__ == "__main__":
    main()
