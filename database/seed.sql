insert into organizations (id, name)
values ('00000000-0000-0000-0000-000000000001', 'Eter Tempus')
on conflict do nothing;

insert into resources (organization_id, code, name, type, unit, minimum_stock)
values
  ('00000000-0000-0000-0000-000000000001', 'MP-0001', 'Te negro', 'raw_material', 'g', 100),
  ('00000000-0000-0000-0000-000000000001', 'MP-0002', 'Naranja', 'raw_material', 'g', 50),
  ('00000000-0000-0000-0000-000000000001', 'MP-0003', 'Rosa', 'raw_material', 'g', 25),
  ('00000000-0000-0000-0000-000000000001', 'MP-0004', 'Cardamomo', 'raw_material', 'g', 20),
  ('00000000-0000-0000-0000-000000000001', 'PR-0001', 'Rosa del Alba', 'product', 'unit', 5),
  ('00000000-0000-0000-0000-000000000001', 'PK-0001', 'Doypack 20 g', 'packaging', 'unit', 20)
on conflict do nothing;

insert into inventory_movements (organization_id, resource_id, type, quantity, unit, reason)
select
  '00000000-0000-0000-0000-000000000001',
  r.id,
  'adjustment',
  case r.code
    when 'MP-0001' then 1000
    when 'MP-0002' then 500
    when 'MP-0003' then 200
    when 'MP-0004' then 100
    when 'PK-0001' then 50
  end,
  r.unit,
  'Carga inicial de stock'
from resources r
where r.organization_id = '00000000-0000-0000-0000-000000000001'
  and r.code in ('MP-0001', 'MP-0002', 'MP-0003', 'MP-0004', 'PK-0001')
  and not exists (
    select 1
    from inventory_movements m
    where m.organization_id = r.organization_id
      and m.resource_id = r.id
      and m.reason = 'Carga inicial de stock'
  );

insert into formulas (organization_id, product_resource_id, name, version, status, active_version, notes)
select
  '00000000-0000-0000-0000-000000000001',
  p.id,
  'Rosa del Alba',
  1,
  'active',
  true,
  'Formula inicial de prueba'
from resources p
where p.organization_id = '00000000-0000-0000-0000-000000000001'
  and p.code = 'PR-0001'
on conflict do nothing;

insert into formula_items (formula_id, ingredient_resource_id, percentage, sort_order)
select f.id, r.id, v.percentage, v.sort_order
from formulas f
join (
  values
    ('MP-0001', 68.00, 1),
    ('MP-0002', 20.00, 2),
    ('MP-0003', 7.00, 3),
    ('MP-0004', 5.00, 4)
) as v(code, percentage, sort_order) on true
join resources r
  on r.organization_id = f.organization_id
 and r.code = v.code
where f.organization_id = '00000000-0000-0000-0000-000000000001'
  and f.name = 'Rosa del Alba'
  and f.version = 1
on conflict do nothing;

insert into payment_methods (organization_id, name)
select '00000000-0000-0000-0000-000000000001', v.name
from (
  values
    ('Efectivo'),
    ('Transferencia'),
    ('Debito'),
    ('Credito'),
    ('Mercado Pago'),
    ('Otro')
) as v(name)
on conflict do nothing;

insert into sales_channels (organization_id, name, source)
select '00000000-0000-0000-0000-000000000001', v.name, 'system'
from (
  values
    ('Venta directa'),
    ('Feria'),
    ('Punto de venta'),
    ('Instagram'),
    ('WhatsApp'),
    ('Encargo'),
    ('Otro')
) as v(name)
on conflict do nothing;

insert into points_of_sale (organization_id, name)
select '00000000-0000-0000-0000-000000000001', v.name
from (
  values
    ('General'),
    ('Montevideo Mistico'),
    ('La CoMarca'),
    ('Samaras')
) as v(name)
on conflict do nothing;

insert into suppliers (organization_id, name)
select '00000000-0000-0000-0000-000000000001', v.name
from (
  values
    ('Niter'),
    ('Casa Singer'),
    ('Otro')
) as v(name)
on conflict do nothing;
