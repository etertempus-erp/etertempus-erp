do $$
begin
  if not exists (select 1 from pg_type where typname = 'purchase_status') then
    create type purchase_status as enum (
      'draft',
      'confirmed'
    );
  end if;
end $$;

create table if not exists purchases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  code text not null,
  purchase_date date not null,
  supplier_name text not null,
  receipt_number text,
  status purchase_status not null default 'draft',
  subtotal numeric(14, 2) not null check (subtotal >= 0),
  total numeric(14, 2) not null check (total >= 0),
  notes text,
  confirmed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);

create table if not exists purchase_details (
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
  add column if not exists purchase_id uuid references purchases(id);

create index if not exists idx_purchases_org_date on purchases(organization_id, purchase_date);
create index if not exists idx_purchases_status on purchases(organization_id, status);
create index if not exists idx_purchase_details_purchase on purchase_details(purchase_id);
create index if not exists idx_purchase_details_resource on purchase_details(resource_id);
create index if not exists idx_movements_purchase on inventory_movements(purchase_id);
