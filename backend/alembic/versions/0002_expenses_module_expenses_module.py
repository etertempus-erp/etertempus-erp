"""expenses module

Revision ID: 0002_expenses_module
Revises: 0001_initial_schema
Create Date: 2026-07-27 18:45:21.670796+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



revision: str = '0002_expenses_module'
down_revision: Union[str, None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            create table if not exists expenses (
              id uuid primary key default gen_random_uuid(),
              organization_id uuid not null references organizations(id),
              expense_date date not null,
              category_id uuid not null references expense_categories(id),
              description text not null,
              amount numeric(14, 2) not null check (amount > 0),
              payment_method_id uuid not null references payment_methods(id),
              supplier_name text,
              receipt_number text,
              notes text,
              status text not null default 'confirmed' check (status in ('confirmed', 'cancelled')),
              origin text not null default 'system' check (origin in ('system', 'imported')),
              cancelled_at timestamptz,
              cancellation_reason text,
              cashbox_entry_id uuid,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now()
            );

            create index if not exists idx_expenses_org_date on expenses(organization_id, expense_date);
            create index if not exists idx_expenses_category on expenses(category_id);
            create index if not exists idx_expenses_payment on expenses(payment_method_id);
            create index if not exists idx_expenses_status_origin on expenses(organization_id, status, origin);
            create index if not exists idx_expenses_supplier on expenses(organization_id, supplier_name);

            insert into expense_categories (organization_id, name, source)
            select o.id, category_name, 'system default'
            from organizations o
            cross join (
              values
                ('Alquiler'),
                ('Comisiones'),
                ('Comunicacion'),
                ('Publicidad'),
                ('Transporte'),
                ('Ferias y eventos'),
                ('Formacion'),
                ('Servicios'),
                ('Packaging no inventariable'),
                ('Limpieza'),
                ('Herramientas'),
                ('Mantenimiento'),
                ('Impuestos'),
                ('Otros')
            ) as initial_categories(category_name)
            where not exists (
              select 1
              from expense_categories ec
              where ec.organization_id = o.id
                and lower(ec.name) = lower(initial_categories.category_name)
            );
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("drop table if exists expenses;"))
