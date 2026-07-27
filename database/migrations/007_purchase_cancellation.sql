do $$
begin
    if not exists (
        select 1
        from pg_enum e
        join pg_type t on t.oid = e.enumtypid
        where t.typname = 'purchase_status'
          and e.enumlabel = 'cancelled'
    ) then
        alter type purchase_status add value 'cancelled';
    end if;
end $$;

do $$
begin
    if not exists (
        select 1
        from pg_enum e
        join pg_type t on t.oid = e.enumtypid
        where t.typname = 'movement_type'
          and e.enumlabel = 'purchase_cancellation'
    ) then
        alter type movement_type add value 'purchase_cancellation';
    end if;
end $$;

alter table purchases
    add column if not exists cancelled_at timestamptz,
    add column if not exists cancellation_reason text;
