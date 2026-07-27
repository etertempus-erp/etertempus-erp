update resources
set minimum_stock = 0
where minimum_stock < 0;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'resources_minimum_stock_non_negative'
  ) then
    alter table resources
      add constraint resources_minimum_stock_non_negative check (minimum_stock >= 0);
  end if;
end $$;

create table if not exists sales_channels (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  source text not null default 'manual',
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists expense_categories (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  source text not null default 'manual',
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists imported_sales (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  sale_date date not null,
  customer_name text,
  department text,
  channel_name text,
  product_name text not null,
  quantity numeric(14, 3) not null check (quantity >= 0),
  unit_price numeric(14, 2) check (unit_price >= 0),
  total_amount numeric(14, 2) check (total_amount >= 0),
  payment_method text,
  source_sheet text not null,
  source_row integer not null,
  control_status text,
  created_at timestamptz not null default now(),
  unique (organization_id, source_sheet, source_row, product_name)
);

create table if not exists imported_expenses (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  expense_date date not null,
  category_name text not null,
  supplier_name text,
  amount numeric(14, 2) not null check (amount >= 0),
  payment_method text,
  source_sheet text not null,
  source_row integer not null,
  control_status text,
  created_at timestamptz not null default now(),
  unique (organization_id, source_sheet, source_row, category_name, amount)
);

create index if not exists idx_imported_sales_date on imported_sales(organization_id, sale_date);
create index if not exists idx_imported_expenses_date on imported_expenses(organization_id, expense_date);
