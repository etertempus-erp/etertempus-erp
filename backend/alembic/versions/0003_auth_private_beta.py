"""auth private beta

Revision ID: 0003_auth_private_beta
Revises: 0002_expenses_module
Create Date: 2026-07-27 20:20:00.000000+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_auth_private_beta"
down_revision: Union[str, None] = "0002_expenses_module"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            do $$
            begin
              if not exists (select 1 from pg_type where typname = 'user_role') then
                create type user_role as enum ('admin', 'operator', 'viewer');
              end if;
            end $$;

            create table if not exists users (
              id uuid primary key default gen_random_uuid(),
              organization_id uuid not null references organizations(id),
              email varchar(255) not null,
              name text not null,
              password_hash text not null,
              role user_role not null default 'operator',
              active boolean not null default true,
              created_at timestamptz not null default now(),
              updated_at timestamptz not null default now(),
              unique (organization_id, email)
            );

            create index if not exists idx_users_org_role on users(organization_id, role);

            create table if not exists user_sessions (
              id uuid primary key default gen_random_uuid(),
              user_id uuid not null references users(id),
              token_hash varchar(128) not null unique,
              expires_at timestamptz not null,
              revoked_at timestamptz,
              created_at timestamptz not null default now()
            );

            create index if not exists idx_user_sessions_active
              on user_sessions(user_id, expires_at)
              where revoked_at is null;

            alter table production_batches
              add column if not exists created_by_user_id uuid references users(id);

            alter table inventory_movements
              add column if not exists created_by_user_id uuid references users(id);

            alter table purchases
              add column if not exists created_by_user_id uuid references users(id),
              add column if not exists confirmed_by_user_id uuid references users(id),
              add column if not exists cancelled_by_user_id uuid references users(id);

            alter table sales
              add column if not exists created_by_user_id uuid references users(id),
              add column if not exists cancelled_by_user_id uuid references users(id);

            alter table expenses
              add column if not exists created_by_user_id uuid references users(id),
              add column if not exists cancelled_by_user_id uuid references users(id);
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            alter table expenses
              drop column if exists cancelled_by_user_id,
              drop column if exists created_by_user_id;

            alter table sales
              drop column if exists cancelled_by_user_id,
              drop column if exists created_by_user_id;

            alter table purchases
              drop column if exists cancelled_by_user_id,
              drop column if exists confirmed_by_user_id,
              drop column if exists created_by_user_id;

            alter table inventory_movements drop column if exists created_by_user_id;
            alter table production_batches drop column if exists created_by_user_id;
            drop table if exists user_sessions;
            drop table if exists users;
            drop type if exists user_role;
            """
        )
    )
