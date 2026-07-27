from __future__ import annotations

import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


PRICE_COSTS_FILE = Path(r"C:\Users\Dhioyi\Desktop\eTER TEMPUS gESTION\PRECIOS Y COSTOS.xlsx")
MANAGEMENT_FILE = Path(r"C:\Users\Dhioyi\Desktop\eTER TEMPUS gESTION\gestion diaria mensual anual.xlsx")
MONTH_SHEETS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Setiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def clean_text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def display_text(value: Any) -> str:
    return strip_accents(clean_text(value))


def number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            value = value.replace("$", "").replace(" ", "").replace(",", ".")
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number


def normalize_name(value: str) -> str:
    ascii_value = strip_accents(value)
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()


def excel_date(value: Any) -> str | None:
    if hasattr(value, "date"):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def payment_method(row: pd.Series, columns: list[int], labels: list[str]) -> str | None:
    for column, label in zip(columns, labels):
        amount = number_or_none(row.iloc[column] if len(row) > column else None)
        if amount is not None and amount > 0:
            return label
    return None


def resource_type_for_category(category: str) -> str | None:
    normalized = normalize_name(category)
    if normalized in {"tes", "especias", "hierbas", "fruta"}:
        return "raw_material"
    if normalized == "packaging":
        return "packaging"
    if normalized == "accesorios para te":
        return "product"
    return None


def code_prefix(resource_type: str) -> str:
    return {
        "raw_material": "MP",
        "packaging": "PK",
        "product": "PR",
        "mix": "MX",
    }[resource_type]


def extract_resources(workbook: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    df = pd.read_excel(workbook, sheet_name="Materias Primas e Insumos", header=None)
    effective_date = excel_date(df.iat[0, 1]) if df.shape[0] > 0 and df.shape[1] > 1 else None
    current_category = ""
    resources: list[dict[str, Any]] = []
    costs: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        category = display_text(row.iloc[0] if len(row) > 0 else "")
        name = display_text(row.iloc[1] if len(row) > 1 else "")
        plant_cost = number_or_none(row.iloc[2] if len(row) > 2 else None)
        sale_or_kg_price = number_or_none(row.iloc[3] if len(row) > 3 else None)
        supplier = display_text(row.iloc[4] if len(row) > 4 else "")

        if category:
            current_category = category
        resource_type = resource_type_for_category(current_category)
        if not name or not resource_type:
            continue
        if normalize_name(name) in {"materia prima", "insumos"}:
            continue

        unit = "unit" if resource_type in {"packaging", "product"} else "g"
        cost_amount = plant_cost
        if resource_type == "raw_material" and plant_cost is not None:
            cost_amount = plant_cost / 1000

        resources.append(
            {
                "name": name,
                "normalized_name": normalize_name(name),
                "type": resource_type,
                "unit": unit,
                "category": current_category,
            }
        )
        if cost_amount is not None:
            costs.append(
                {
                    "resource_name": name,
                    "normalized_name": normalize_name(name),
                    "amount": round(cost_amount, 4),
                    "unit": unit,
                    "supplier_name": supplier or None,
                    "effective_date": effective_date,
                    "source": "PRECIOS Y COSTOS.xlsx / Materias Primas e Insumos",
                    "notes": (
                        "Costo por gramo calculado desde puesto en planta por kg."
                        if resource_type == "raw_material"
                        else "Costo unitario importado desde puesto en planta."
                    ),
                }
            )

        if resource_type == "product" and sale_or_kg_price is not None:
            costs.append(
                {
                    "resource_name": name,
                    "normalized_name": normalize_name(name),
                    "amount": round(cost_amount or 0, 4),
                    "unit": unit,
                    "supplier_name": supplier or None,
                    "effective_date": effective_date,
                    "source": "PRECIOS Y COSTOS.xlsx / Accesorios",
                    "notes": f"Precio de venta observado en Excel: ${sale_or_kg_price:.2f}.",
                }
            )

    return resources, costs


def extract_product_prices(workbook: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    df = pd.read_excel(workbook, sheet_name="RESUMEN", header=None)
    effective_date = None
    products: list[dict[str, Any]] = []
    prices: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        name = display_text(row.iloc[0] if len(row) > 0 else "")
        if not name or normalize_name(name) in {"producto", "listado de precios y costos"}:
            continue

        variable_cost = number_or_none(row.iloc[1] if len(row) > 1 else None)
        sale_price = number_or_none(row.iloc[2] if len(row) > 2 else None)
        contribution_margin = number_or_none(row.iloc[3] if len(row) > 3 else None)
        contribution_margin_pct = number_or_none(row.iloc[4] if len(row) > 4 else None)
        if sale_price is None:
            continue

        products.append(
            {
                "name": name.title(),
                "normalized_name": normalize_name(name),
                "type": "product",
                "unit": "unit",
                "category": "Productos",
            }
        )
        prices.append(
            {
                "product_name": name.title(),
                "normalized_name": normalize_name(name),
                "price_list_name": "Publico",
                "sale_price": round(sale_price, 2),
                "variable_cost_snapshot": round(variable_cost, 2) if variable_cost is not None else None,
                "contribution_margin": round(contribution_margin, 2) if contribution_margin is not None else None,
                "contribution_margin_pct": (
                    round(contribution_margin_pct, 4) if contribution_margin_pct is not None else None
                ),
                "effective_date": effective_date,
                "source": "PRECIOS Y COSTOS.xlsx / RESUMEN",
            }
        )

    return products, prices


def extract_formulas(workbook: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    df = pd.read_excel(workbook, sheet_name="Fichas Productos", header=None)
    formulas: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    row_index = 0

    while row_index < len(df):
        marker = normalize_name(display_text(df.iat[row_index, 1] if df.shape[1] > 1 else ""))
        if marker != "ficha tecnica":
            row_index += 1
            continue

        product_name = ""
        for candidate_index in range(row_index + 1, min(row_index + 5, len(df))):
            candidate = display_text(df.iat[candidate_index, 1] if df.shape[1] > 1 else "")
            if candidate:
                product_name = candidate
                break

        if not product_name:
            row_index += 1
            continue

        formula_items: list[dict[str, Any]] = []
        header_index = None
        for candidate_index in range(row_index + 1, min(row_index + 10, len(df))):
            label = normalize_name(display_text(df.iat[candidate_index, 1] if df.shape[1] > 1 else ""))
            if label == "materia prima insumos":
                header_index = candidate_index
                break

        if header_index is None:
            row_index += 1
            continue

        item_index = header_index + 1
        while item_index < len(df):
            ingredient_name = display_text(df.iat[item_index, 1] if df.shape[1] > 1 else "")
            ingredient_key = normalize_name(ingredient_name)
            if ingredient_key.startswith("total materia prima") or ingredient_key in {"packaging", "mano de obra"}:
                break

            quantity = number_or_none(df.iat[item_index, 2] if df.shape[1] > 2 else None)
            if ingredient_name and quantity is not None and quantity > 0:
                formula_items.append(
                    {
                        "ingredient_name": ingredient_name,
                        "normalized_name": normalize_name(ingredient_name),
                        "quantity": quantity,
                    }
                )
            item_index += 1

        total_quantity = sum(item["quantity"] for item in formula_items)
        if total_quantity > 0 and formula_items:
            percentages = []
            running_total = 0.0
            for index, item in enumerate(formula_items):
                if index == len(formula_items) - 1:
                    percentage = round(100 - running_total, 2)
                else:
                    percentage = round(item["quantity"] / total_quantity * 100, 2)
                    running_total += percentage
                percentages.append({**item, "percentage": percentage, "sort_order": index + 1})

            formulas.append(
                {
                    "name": product_name.title(),
                    "normalized_name": normalize_name(product_name),
                    "version": 1,
                    "status": "active",
                    "active_version": True,
                    "notes": "Importada desde PRECIOS Y COSTOS.xlsx / Fichas Productos",
                    "items": percentages,
                }
            )
            products.append(
                {
                    "name": product_name.title(),
                    "normalized_name": normalize_name(product_name),
                    "type": "product",
                    "unit": "unit",
                    "category": "Productos",
                }
            )

        row_index = max(item_index + 1, row_index + 1)

    return formulas, products


def extract_management_catalogs(workbook: Path) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    df = pd.read_excel(workbook, sheet_name="Datos", header=None)
    products: list[dict[str, Any]] = []
    expense_categories: list[str] = []
    channels: list[str] = []

    for _, row in df.iterrows():
        product = display_text(row.iloc[1] if len(row) > 1 else "")
        category = display_text(row.iloc[3] if len(row) > 3 else "")
        channel = display_text(row.iloc[7] if len(row) > 7 else "")

        if product and normalize_name(product) != "productos":
            products.append(
                {
                    "name": product.title(),
                    "normalized_name": normalize_name(product),
                    "type": "product",
                    "unit": "unit",
                    "category": "Productos",
                }
            )
        if category and normalize_name(category) != "conceptos":
            expense_categories.append(category)
        if channel and normalize_name(channel) != "canal":
            channels.append(channel)

    return products, sorted(set(expense_categories)), sorted(set(channels))


def extract_management_movements(workbook: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sales: list[dict[str, Any]] = []
    expenses: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []

    for sheet in MONTH_SHEETS:
        df = pd.read_excel(workbook, sheet_name=sheet, header=None)
        for row_index, row in df.iterrows():
            sale_date = excel_date(row.iloc[0] if len(row) > 0 else None)
            product_name = display_text(row.iloc[4] if len(row) > 4 else "")
            quantity = number_or_none(row.iloc[5] if len(row) > 5 else None)
            unit_price = number_or_none(row.iloc[6] if len(row) > 6 else None)
            total_amount = number_or_none(row.iloc[7] if len(row) > 7 else None)
            if (
                sale_date
                and product_name
                and quantity is not None
                and quantity >= 0
                and (total_amount is None or total_amount >= 0)
                and (unit_price is None or unit_price >= 0)
                and (quantity > 0 or (total_amount is not None and total_amount > 0))
            ):
                customer_name = display_text(row.iloc[1] if len(row) > 1 else "")
                department = display_text(row.iloc[2] if len(row) > 2 else "")
                channel_name = display_text(row.iloc[3] if len(row) > 3 else "")
                sales.append(
                    {
                        "sale_date": sale_date,
                        "customer_name": customer_name or None,
                        "department": department or None,
                        "channel_name": channel_name or None,
                        "product_name": product_name,
                        "normalized_name": normalize_name(product_name),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "total_amount": total_amount,
                        "payment_method": payment_method(row, [8, 9, 10], ["Efectivo", "Mercado Pago", "Banco"]),
                        "source_sheet": sheet,
                        "source_row": row_index + 1,
                        "control_status": display_text(row.iloc[11] if len(row) > 11 else "") or None,
                    }
                )
                products.append(
                    {
                        "name": product_name.title(),
                        "normalized_name": normalize_name(product_name),
                        "type": "product",
                        "unit": "unit",
                        "category": "Productos",
                    }
                )

            expense_date = excel_date(row.iloc[13] if len(row) > 13 else None)
            category_name = display_text(row.iloc[14] if len(row) > 14 else "")
            amount = number_or_none(row.iloc[16] if len(row) > 16 else None)
            if expense_date and category_name and amount is not None and amount >= 0 and amount > 0:
                expenses.append(
                    {
                        "expense_date": expense_date,
                        "category_name": category_name,
                        "supplier_name": display_text(row.iloc[15] if len(row) > 15 else "") or None,
                        "amount": amount,
                        "payment_method": payment_method(row, [17, 18, 19], ["Efectivo", "Mercado Pago", "Banco"]),
                        "source_sheet": sheet,
                        "source_row": row_index + 1,
                        "control_status": display_text(row.iloc[20] if len(row) > 20 else "") or None,
                    }
                )

    return sales, expenses, products


def dedupe_rows(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for row in rows:
        value = row[key]
        if value in seen:
            continue
        seen.add(value)
        result.append(row)
    return result


def main() -> None:
    if not PRICE_COSTS_FILE.exists():
        raise SystemExit(f"No encontre el archivo: {PRICE_COSTS_FILE}")
    if not MANAGEMENT_FILE.exists():
        raise SystemExit(f"No encontre el archivo: {MANAGEMENT_FILE}")

    resources, costs = extract_resources(PRICE_COSTS_FILE)
    product_resources, product_prices = extract_product_prices(PRICE_COSTS_FILE)
    formulas, formula_products = extract_formulas(PRICE_COSTS_FILE)
    management_products, expense_categories, sales_channels = extract_management_catalogs(MANAGEMENT_FILE)
    imported_sales, imported_expenses, sales_products = extract_management_movements(MANAGEMENT_FILE)
    formula_ingredients = [
        {
            "name": item["ingredient_name"],
            "normalized_name": item["normalized_name"],
            "type": "raw_material",
            "unit": "g",
            "category": "Ingredientes de formulas",
        }
        for formula in formulas
        for item in formula["items"]
    ]
    resources = dedupe_rows(
        resources + product_resources + formula_products + management_products + sales_products + formula_ingredients,
        "normalized_name",
    )

    json.dump(
        {
            "resources": resources,
            "resource_costs": costs,
            "product_prices": product_prices,
            "formulas": formulas,
            "sales_channels": sales_channels,
            "expense_categories": expense_categories,
            "imported_sales": imported_sales,
            "imported_expenses": imported_expenses,
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )


if __name__ == "__main__":
    main()
