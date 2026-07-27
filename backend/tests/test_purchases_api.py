from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def db_scalar(sql: str, params: dict):
    with SessionLocal() as db:
        return db.execute(text(sql), params).scalar()


def db_execute(sql: str, params: dict | None = None):
    with SessionLocal() as db:
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            db.execute(text(statement), params or {})
        db.commit()


def create_fixture() -> dict:
    organization_id = str(uuid4())
    resource_id = str(uuid4())
    second_resource_id = str(uuid4())
    db_execute(
        """
        insert into organizations (id, name) values (:organization_id, :name);
        insert into resources (id, organization_id, code, name, type, unit)
        values (:resource_id, :organization_id, 'MP-COMPRA-1', 'Lavanda test', 'raw_material', 'g');
        insert into resources (id, organization_id, code, name, type, unit)
        values (:second_resource_id, :organization_id, 'MP-COMPRA-2', 'Cedron test', 'raw_material', 'g');
        """,
        {
            "organization_id": organization_id,
            "name": f"Org compras {organization_id}",
            "resource_id": resource_id,
            "second_resource_id": second_resource_id,
        },
    )
    return {"organization_id": organization_id, "resource_id": resource_id, "second_resource_id": second_resource_id}


def cleanup_fixture(organization_id: str):
    db_execute(
        """
        delete from resource_costs where organization_id = :organization_id;
        delete from inventory_movements where organization_id = :organization_id;
        delete from purchase_details where organization_id = :organization_id;
        delete from purchases where organization_id = :organization_id;
        delete from suppliers where organization_id = :organization_id;
        delete from resources where organization_id = :organization_id;
        delete from organizations where id = :organization_id;
        """,
        {"organization_id": organization_id},
    )


def purchase_payload(fixture: dict) -> dict:
    return {
        "organization_id": fixture["organization_id"],
        "purchase_date": "2026-07-27",
        "supplier_name": "Proveedor test",
        "receipt_number": "A-001",
        "notes": "Compra de prueba",
        "lines": [
            {
                "resource_id": fixture["resource_id"],
                "quantity": 250,
                "unit": "g",
                "unit_price": 1.5,
            }
        ],
    }


def purchase_payload_with_price(fixture: dict, unit_price: Decimal | float | int) -> dict:
    payload = purchase_payload(fixture)
    payload["lines"][0]["unit_price"] = float(unit_price)
    return payload


def purchase_payload_with_many_lines(fixture: dict) -> dict:
    payload = purchase_payload(fixture)
    payload["lines"] = [
        {
            "resource_id": fixture["resource_id"],
            "quantity": 250,
            "unit": "g",
            "unit_price": 1.5,
        },
        {
            "resource_id": fixture["second_resource_id"],
            "quantity": 1000,
            "unit": "g",
            "unit_price": 0.8,
        },
    ]
    return payload


def latest_cost(resource_id: str, organization_id: str):
    return db_scalar(
        """
        select amount
        from resource_costs
        where organization_id = :org
          and resource_id = :resource
          and active = true
        order by effective_date desc nulls last, created_at desc
        limit 1
        """,
        {"org": organization_id, "resource": resource_id},
    )


def stock_for(resource_id: str, organization_id: str):
    return db_scalar(
        """
        select coalesce(sum(quantity), 0)
        from inventory_movements
        where organization_id = :org and resource_id = :resource
        """,
        {"org": organization_id, "resource": resource_id},
    )


def test_create_purchase_draft_does_not_change_stock():
    fixture = create_fixture()
    try:
        response = client.post("/purchases", json=purchase_payload(fixture))
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "draft"
        assert body["total"] == "375.00"

        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :resource",
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        assert stock == Decimal("0")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_confirm_purchase_increases_stock_and_generates_movement_and_cost():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload(fixture)).json()
        response = client.post(f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "confirmed"
        assert len(body["movements"]) == 1
        assert body["movements"][0]["type"] == "purchase"
        assert body["movements"][0]["quantity"] == "250.000"

        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :resource",
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        cost = db_scalar(
            "select amount from resource_costs where organization_id = :org and resource_id = :resource and source = 'purchase'",
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        assert stock == Decimal("250.000")
        assert cost == Decimal("1.5000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cannot_confirm_purchase_twice():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload(fixture)).json()
        first = client.post(f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}", json={})
        second = client.post(f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}", json={})
        assert first.status_code == 200
        assert second.status_code == 422
        assert "ya estaba confirmada" in second.json()["detail"]
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_draft_purchase_does_not_change_stock_and_cannot_confirm_later():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload(fixture)).json()
        cancel = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Pedido no enviado"},
        )
        assert cancel.status_code == 200
        assert cancel.json()["status"] == "cancelled"

        confirm = client.post(f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}", json={})
        assert confirm.status_code == 422
        assert "compra anulada" in confirm.json()["detail"]

        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :resource",
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        assert stock == Decimal("0")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_confirmed_purchase_reverses_stock_with_cancellation_movement():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload(fixture)).json()
        confirm = client.post(f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}", json={})
        assert confirm.status_code == 200

        cancel = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Devolucion del proveedor"},
        )
        assert cancel.status_code == 200
        body = cancel.json()
        assert body["status"] == "cancelled"
        assert [movement["type"] for movement in body["movements"]] == ["purchase", "purchase_cancellation"]

        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :resource",
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        assert stock == Decimal("0.000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_second_purchase_restores_previous_valid_cost():
    fixture = create_fixture()
    try:
        first_purchase = client.post("/purchases", json=purchase_payload_with_price(fixture, 0.6)).json()
        first_confirm = client.post(
            f"/purchases/{first_purchase['id']}/confirm?organization_id={fixture['organization_id']}",
            json={},
        )
        assert first_confirm.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.6000")

        second_purchase = client.post("/purchases", json=purchase_payload_with_price(fixture, 0.8)).json()
        second_confirm = client.post(
            f"/purchases/{second_purchase['id']}/confirm?organization_id={fixture['organization_id']}",
            json={},
        )
        assert second_confirm.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.8000")

        cancel = client.post(
            f"/purchases/{second_purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Pedido devuelto"},
        )
        assert cancel.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.6000")
        inactive_costs = db_scalar(
            """
            select count(*)
            from resource_costs
            where organization_id = :org
              and purchase_id = :purchase_id
              and active = false
            """,
            {"org": fixture["organization_id"], "purchase_id": second_purchase["id"]},
        )
        assert inactive_costs == 1
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_resource_list_ignores_cost_from_cancelled_purchase():
    fixture = create_fixture()
    purchase_id = str(uuid4())
    try:
        db_execute(
            """
            insert into purchases (
              id, organization_id, code, purchase_date, supplier_name, status, subtotal, total, cancelled_at
            )
            values (
              :purchase_id, :org, 'C-CANCELADA', '2026-07-27', 'Proveedor cancelado',
              'cancelled', 200.00, 200.00, now()
            );
            insert into resource_costs (
              organization_id, resource_id, amount, unit, supplier_name, effective_date, source, notes
            )
            values (
              :org, :resource, 0.6000, 'g', 'Importado', '2026-05-31', 'PRECIOS Y COSTOS.xlsx', 'Costo inicial'
            );
            insert into resource_costs (
              organization_id, resource_id, purchase_id, amount, unit, supplier_name, effective_date, source, notes
            )
            values (
              :org, :resource, :purchase_id, 600.0000, 'g', 'Proveedor cancelado', '2026-07-27',
              'purchase', 'Compra C-CANCELADA'
            );
            """,
            {"org": fixture["organization_id"], "resource": fixture["resource_id"], "purchase_id": purchase_id},
        )

        response = client.get(f"/resources?organization_id={fixture['organization_id']}")
        assert response.status_code == 200
        resource = next(item for item in response.json() if item["id"] == fixture["resource_id"])
        assert resource["latest_unit_cost"] == "0.6000"
        assert resource["latest_supplier_name"] == "Importado"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_only_purchase_leaves_no_active_purchase_cost():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload_with_price(fixture, 0.6)).json()
        confirm = client.post(
            f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}",
            json={},
        )
        assert confirm.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.6000")

        cancel = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Pedido cancelado"},
        )
        assert cancel.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) is None
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_only_purchase_falls_back_to_imported_cost():
    fixture = create_fixture()
    try:
        db_execute(
            """
            insert into resource_costs (
              organization_id, resource_id, amount, unit, supplier_name, effective_date, source, notes
            )
            values (
              :org, :resource, 0.6000, 'g', 'Importado', '2026-05-31', 'PRECIOS Y COSTOS.xlsx', 'Costo inicial'
            );
            """,
            {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
        )
        purchase = client.post("/purchases", json=purchase_payload_with_price(fixture, 0.8)).json()
        confirm = client.post(
            f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}",
            json={},
        )
        assert confirm.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.8000")

        cancel = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Pedido cancelado"},
        )
        assert cancel.status_code == 200
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.6000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_purchase_with_many_lines_reverses_stock_and_costs():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload_with_many_lines(fixture)).json()
        confirm = client.post(
            f"/purchases/{purchase['id']}/confirm?organization_id={fixture['organization_id']}",
            json={},
        )
        assert confirm.status_code == 200
        assert stock_for(fixture["resource_id"], fixture["organization_id"]) == Decimal("250.000")
        assert stock_for(fixture["second_resource_id"], fixture["organization_id"]) == Decimal("1000.000")
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) == Decimal("1.5000")
        assert latest_cost(fixture["second_resource_id"], fixture["organization_id"]) == Decimal("0.8000")

        cancel = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Proveedor no envio"},
        )
        assert cancel.status_code == 200
        assert stock_for(fixture["resource_id"], fixture["organization_id"]) == Decimal("0.000")
        assert stock_for(fixture["second_resource_id"], fixture["organization_id"]) == Decimal("0.000")
        assert latest_cost(fixture["resource_id"], fixture["organization_id"]) is None
        assert latest_cost(fixture["second_resource_id"], fixture["organization_id"]) is None
        assert [movement["type"] for movement in cancel.json()["movements"]] == [
            "purchase",
            "purchase",
            "purchase_cancellation",
            "purchase_cancellation",
        ]
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cannot_cancel_purchase_twice():
    fixture = create_fixture()
    try:
        purchase = client.post("/purchases", json=purchase_payload(fixture)).json()
        first = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Prueba"},
        )
        second = client.post(
            f"/purchases/{purchase['id']}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Prueba repetida"},
        )
        assert first.status_code == 200
        assert second.status_code == 422
        assert "ya estaba anulada" in second.json()["detail"]
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_reject_invalid_purchase_values():
    fixture = create_fixture()
    try:
        for line in [
            {"resource_id": fixture["resource_id"], "quantity": 0, "unit": "g", "unit_price": 1},
            {"resource_id": fixture["resource_id"], "quantity": -1, "unit": "g", "unit_price": 1},
            {"resource_id": fixture["resource_id"], "quantity": 1, "unit": "g", "unit_price": -1},
        ]:
            payload = purchase_payload(fixture)
            payload["lines"] = [line]
            response = client.post("/purchases", json=payload)
            assert response.status_code == 422
    finally:
        cleanup_fixture(fixture["organization_id"])
