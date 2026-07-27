from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter()

TYPE_GROUPS = {
    "compras": ["purchase"],
    "ventas": ["sale"],
    "produccion": ["production_consumption", "production_output", "packaging"],
    "ajustes": ["adjustment"],
    "anulaciones": ["purchase_cancellation", "sale_cancellation"],
}


@router.get("")
def list_movements(
    organization_id: UUID = Query(...),
    type_group: str | None = Query(default=None),
    limit: int = Query(default=80, ge=1, le=200),
    db: Session = Depends(get_db),
):
    params: dict[str, object] = {"organization_id": organization_id, "limit": limit}
    where = "where m.organization_id = :organization_id"
    if type_group:
        types = TYPE_GROUPS.get(type_group, [type_group])
        where += " and m.type = any(:types)"
        params["types"] = types

    return [
        dict(row)
        for row in db.execute(
            text(
                f"""
                select
                  m.id::text,
                  m.occurred_at,
                  m.type,
                  r.name as resource_name,
                  r.code as resource_code,
                  m.quantity,
                  m.unit,
                  m.reason,
                  case
                    when m.purchase_id is not null then 'Compra'
                    when m.production_batch_id is not null then 'Produccion'
                    when m.type in ('sale', 'sale_cancellation') then 'Venta'
                    else 'Inventario'
                  end as origin,
                  coalesce(p.code, pb.batch_number, m.reason) as document_label
                from inventory_movements m
                join resources r on r.id = m.resource_id
                left join purchases p on p.id = m.purchase_id
                left join production_batches pb on pb.id = m.production_batch_id
                {where}
                order by m.occurred_at desc, m.created_at desc
                limit :limit
                """
            ),
            params,
        ).mappings()
    ]
