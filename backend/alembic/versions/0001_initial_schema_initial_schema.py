"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-07-27 18:40:06.596921+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pathlib import Path



revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "schema_snapshots" / "0001_initial_schema.sql"
    op.execute(sa.text(schema_path.read_text(encoding="utf-8")))


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            drop view if exists formula_percentage_totals;
            drop view if exists current_stock;

            drop table if exists sale_inventory_movements;
            drop table if exists sale_details;
            drop table if exists sales;
            drop table if exists imported_expenses;
            drop table if exists imported_sales;
            drop table if exists purchase_details;
            drop table if exists resource_costs;
            drop table if exists inventory_movements;
            drop table if exists purchases;
            drop table if exists suppliers;
            drop table if exists product_prices;
            drop table if exists production_batches;
            drop table if exists formula_items;
            drop table if exists formulas;
            drop table if exists points_of_sale;
            drop table if exists payment_methods;
            drop table if exists expense_categories;
            drop table if exists sales_channels;
            drop table if exists resources;
            drop table if exists organizations;

            drop type if exists purchase_status;
            drop type if exists sale_status;
            drop type if exists movement_type;
            drop type if exists batch_status;
            drop type if exists formula_status;
            drop type if exists unit_type;
            drop type if exists resource_type;
            """
        )
    )
