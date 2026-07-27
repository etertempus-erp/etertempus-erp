do $$
begin
  if not exists (
    select 1 from pg_enum e
    join pg_type t on t.oid = e.enumtypid
    where t.typname = 'movement_type'
      and e.enumlabel = 'sale_cancellation'
  ) then
    alter type movement_type add value 'sale_cancellation';
  end if;
end $$;

do $$
begin
  if not exists (select 1 from pg_type where typname = 'sale_status') then
    create type sale_status as enum (
      'draft',
      'confirmed',
      'cancelled'
    );
  end if;
end $$;

create table if not exists payment_methods (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists points_of_sale (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (organization_id, name)
);

create table if not exists sales (
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

create table if not exists sale_details (
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

create table if not exists sale_inventory_movements (
  id uuid primary key default gen_random_uuid(),
  sale_detail_id uuid not null references sale_details(id) on delete cascade,
  inventory_movement_id uuid not null references inventory_movements(id),
  created_at timestamptz not null default now(),
  unique (sale_detail_id, inventory_movement_id)
);

create index if not exists idx_payment_methods_org on payment_methods(organization_id);
create index if not exists idx_points_of_sale_org on points_of_sale(organization_id);
create index if not exists idx_sales_org_date on sales(organization_id, sale_date);
create index if not exists idx_sales_channel on sales(channel_id);
create index if not exists idx_sales_payment on sales(payment_method_id);
create index if not exists idx_sale_details_sale on sale_details(sale_id);
create index if not exists idx_sale_details_resource on sale_details(resource_id);

insert into payment_methods (organization_id, name)
select o.id, v.name
from organizations o
cross join (
  values
    ('Efectivo'),
    ('Transferencia'),
    ('Debito'),
    ('Credito'),
    ('Mercado Pago'),
    ('Otro')
) as v(name)
on conflict (organization_id, name) do nothing;

insert into sales_channels (organization_id, name, source)
select o.id, v.name, 'system'
from organizations o
cross join (
  values
    ('Venta directa'),
    ('Feria'),
    ('Punto de venta'),
    ('Instagram'),
    ('WhatsApp'),
    ('Encargo'),
    ('Otro')
) as v(name)
on conflict (organization_id, name) do nothing;

insert into points_of_sale (organization_id, name)
select o.id, v.name
from organizations o
cross join (
  values
    ('General'),
    ('Montevideo Mistico'),
    ('La CoMarca'),
    ('Samaras')
) as v(name)
on conflict (organization_id, name) do nothing;
