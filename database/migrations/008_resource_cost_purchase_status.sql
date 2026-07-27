alter table resource_costs
  add column if not exists purchase_id uuid references purchases(id),
  add column if not exists active boolean not null default true;

update resource_costs rc
set purchase_id = p.id
from purchases p
where rc.purchase_id is null
  and rc.organization_id = p.organization_id
  and rc.source = 'purchase'
  and rc.notes = ('Compra ' || p.code);

create index if not exists idx_resource_costs_active
  on resource_costs(organization_id, resource_id, active, effective_date desc, created_at desc);

create index if not exists idx_resource_costs_purchase
  on resource_costs(purchase_id);
