create table if not exists suppliers (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references organizations(id),
  name text not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, name)
);

alter table purchases
  add column if not exists supplier_id uuid references suppliers(id);

create index if not exists idx_suppliers_org_name on suppliers(organization_id, name);
create index if not exists idx_purchases_supplier on purchases(supplier_id);

insert into suppliers (organization_id, name)
select o.id, v.name
from organizations o
cross join (
  values
    ('Niter'),
    ('Casa Singer'),
    ('Otro')
) as v(name)
on conflict (organization_id, name) do nothing;

insert into suppliers (organization_id, name)
select distinct organization_id, supplier_name
from purchases
where supplier_name is not null
  and trim(supplier_name) <> ''
on conflict (organization_id, name) do nothing;

update purchases p
set supplier_id = s.id
from suppliers s
where p.supplier_id is null
  and s.organization_id = p.organization_id
  and s.name = p.supplier_name;
