drop view if exists formula_percentage_totals;

alter table formula_items
  alter column percentage type numeric(8, 2)
  using round(percentage, 2);

create view formula_percentage_totals as
select
  formula_id,
  sum(percentage) as total_percentage
from formula_items
group by formula_id;
