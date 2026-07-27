create extension if not exists "pgcrypto";

create type resource_type as enum (
  'raw_material',
  'packaging',
  'product',
  'mix'
);

create type unit_type as enum (
  'g',
  'kg',
  'ml',
  'unit'
);

create type formula_status as enum (
  'draft',
  'active',
  'archived'
);

create type batch_status as enum (
  'elaborated',
  'partially_packaged',
  'fully_packaged',
  'closed',
  'cancelled'
);

create type movement_type as enum (
  'purchase',
  'purchase_cancellation',
  'production_consumption',
  'production_output',
  'packaging',
  'sale',
  'sale_cancellation',
  'internal_consumption',
  'tasting',
  'development',
  'discard',
  'adjustment'
);

create type sale_status as enum (
  'draft',
  'confirmed',
  'cancelled'
);

create type purchase_status as enum (
  'draft',
  'confirmed',
  'cancelled'
);

create table organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  active boolean not null default true
);

create table resources (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  code text not null,
  name text not null,
  type resource_type not null,
  unit unit_type not null,
  minimum_stock numeric(14, 3) not null default 0 check (minimum_stock >= 0),
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);

create table formulas (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  product_resource_id uuid references resources(id),
  name text not null,
  version integer not null,
  status formula_status not null default 'draft',
  active_version boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, name, version)
);

create table formula_items (
  id uuid primary key default gen_random_uuid(),
  formula_id uuid not null references formulas(id) on delete cascade,
  ingredient_resource_id uuid not null references resources(id),
  percentage numeric(8, 2) not null check (percentage > 0 and percentage <= 100),
  sort_order integer not null default 0,
  unique (formula_id, ingredient_resource_id)
);

create table production_batches (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  batch_number text not null,
  elaboration_date date not null,
  product_resource_id uuid not null references resources(id),
  formula_id uuid not null references formulas(id),
  mix_resource_id uuid not null references resources(id),
  target_weight numeric(14, 3) not null check (target_weight > 0),
  unit unit_type not null default 'g',
  status batch_status not null default 'elaborated',
  ingredient_cost_snapshot numeric(14, 2) not null default 0,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, batch_number)
);

create table inventory_movements (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  resource_id uuid not null references resources(id),
  production_batch_id uuid references production_batches(id),
  purchase_id uuid,
  type movement_type not null,
  quantity numeric(14, 3) not null check (quantity <> 0),
  unit unit_type not null,
  unit_cost_snapshot numeric(14, 4),
  reason text,
  occurred_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create table resource_costs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  resource_id uuid not null references resources(id),
  purchase_id uuid,
  amount numeric(14, 4) not null check (amount >= 0),
  unit unit_type not null,
  supplier_name text,
  effective_date date,
  source text not null default 'manual',
  notes text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table product_prices (
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

create table sales_channels (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  source text not null default 'manual',
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table expense_categories (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  source text not null default 'manual',
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table payment_methods (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table points_of_sale (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table suppliers (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table sales (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  code text not null,
  sale_date date not null,
  channel_id uuid not null references sales_channels(id),
  point_of_sale_id uuid references points_of_sale(id),
  customer_name text,
  payment_method_id uuid not null references payment_methods(id),
  status sale_status not null default 'confirmed',
  subtotal numeric(14, 2) not null check (subtotal >= 0),
  discount_total numeric(14, 2) not null default 0 check (discount_total >= 0),
  total numeric(14, 2) not null check (total >= 0),
  notes text,
  source text not null default 'system',
  created_by text,
  confirmed_at timestamptz,
  cancelled_at timestamptz,
  cancellation_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);

create table sale_details (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  sale_id uuid not null references sales(id) on delete cascade,
  resource_id uuid not null references resources(id),
  quantity numeric(14, 3) not null check (quantity > 0),
  unit_price numeric(14, 2) not null check (unit_price >= 0),
  discount numeric(14, 2) not null default 0 check (discount >= 0),
  line_total numeric(14, 2) not null check (line_total >= 0),
  created_at timestamptz not null default now()
);

create table sale_inventory_movements (
  id uuid primary key default gen_random_uuid(),
  sale_detail_id uuid not null references sale_details(id) on delete cascade,
  inventory_movement_id uuid not null references inventory_movements(id),
  created_at timestamptz not null default now(),
  unique (sale_detail_id, inventory_movement_id)
);

create table purchases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  code text not null,
  purchase_date date not null,
  supplier_id uuid references suppliers(id),
  supplier_name text not null,
  receipt_number text,
  status purchase_status not null default 'draft',
  subtotal numeric(14, 2) not null check (subtotal >= 0),
  total numeric(14, 2) not null check (total >= 0),
  notes text,
  confirmed_at timestamptz,
  cancelled_at timestamptz,
  cancellation_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);

create table purchase_details (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  purchase_id uuid not null references purchases(id) on delete cascade,
  resource_id uuid not null references resources(id),
  quantity numeric(14, 3) not null check (quantity > 0),
  unit unit_type not null,
  unit_price numeric(14, 4) not null check (unit_price >= 0),
  line_total numeric(14, 2) not null check (line_total >= 0),
  created_at timestamptz not null default now()
);

alter table inventory_movements
  add constraint inventory_movements_purchase_id_fkey foreign key (purchase_id) references purchases(id);

alter table resource_costs
  add constraint resource_costs_purchase_id_fkey foreign key (purchase_id) references purchases(id);

create table imported_sales (
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

create table imported_expenses (
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

create index idx_resources_organization_type on resources(organization_id, type);
create index idx_formula_items_formula on formula_items(formula_id);
create index idx_batches_organization_date on production_batches(organization_id, elaboration_date);
create index idx_movements_resource on inventory_movements(resource_id);
create index idx_movements_batch on inventory_movements(production_batch_id);
create index idx_movements_purchase on inventory_movements(purchase_id);
create index idx_resource_costs_resource on resource_costs(resource_id);
create index idx_resource_costs_active on resource_costs(organization_id, resource_id, active, effective_date desc, created_at desc);
create index idx_resource_costs_purchase on resource_costs(purchase_id);
create index idx_product_prices_resource on product_prices(product_resource_id);
create unique index idx_resource_costs_unique_import on resource_costs(
  organization_id,
  resource_id,
  amount,
  unit,
  coalesce(supplier_name, ''),
  coalesce(effective_date, '1900-01-01'::date),
  source
);
create unique index idx_product_prices_unique_import on product_prices(
  organization_id,
  product_resource_id,
  price_list_name,
  sale_price,
  coalesce(effective_date, '1900-01-01'::date),
  source
);
create index idx_imported_sales_date on imported_sales(organization_id, sale_date);
create index idx_imported_expenses_date on imported_expenses(organization_id, expense_date);
create index idx_payment_methods_org on payment_methods(organization_id);
create index idx_points_of_sale_org on points_of_sale(organization_id);
create index idx_suppliers_org_name on suppliers(organization_id, name);
create index idx_sales_org_date on sales(organization_id, sale_date);
create index idx_sales_channel on sales(channel_id);
create index idx_sales_payment on sales(payment_method_id);
create index idx_sale_details_sale on sale_details(sale_id);
create index idx_sale_details_resource on sale_details(resource_id);
create index idx_purchases_org_date on purchases(organization_id, purchase_date);
create index idx_purchases_status on purchases(organization_id, status);
create index idx_purchases_supplier on purchases(supplier_id);
create index idx_purchase_details_purchase on purchase_details(purchase_id);
create index idx_purchase_details_resource on purchase_details(resource_id);

create view current_stock as
select
  organization_id,
  resource_id,
  unit,
  sum(quantity) as quantity
from inventory_movements
group by organization_id, resource_id, unit;

create view formula_percentage_totals as
select
  formula_id,
  sum(percentage) as total_percentage
from formula_items
group by formula_id;
