create table if not exists resource_costs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  resource_id uuid not null references resources(id),
  amount numeric(14, 4) not null check (amount >= 0),
  unit unit_type not null,
  supplier_name text,
  effective_date date,
  source text not null default 'manual',
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists product_prices (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  product_resource_id uuid not null references resources(id),
  price_list_name text not null default 'Publico',
  sale_price numeric(14, 2) not null check (sale_price >= 0),
  variable_cost_snapshot numeric(14, 2),
  contribution_margin numeric(14, 2),
  contribution_margin_pct numeric(8, 4),
  effective_date date,
  source text not null default 'manual',
  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_resource_costs_resource on resource_costs(resource_id);
create index if not exists idx_product_prices_resource on product_prices(product_resource_id);

create unique index if not exists idx_resource_costs_unique_import on resource_costs(
  organization_id,
  resource_id,
  amount,
  unit,
  coalesce(supplier_name, ''),
  coalesce(effective_date, '1900-01-01'::date),
  source
);

create unique index if not exists idx_product_prices_unique_import on product_prices(
  organization_id,
  product_resource_id,
  price_list_name,
  sale_price,
  coalesce(effective_date, '1900-01-01'::date),
  source
);
