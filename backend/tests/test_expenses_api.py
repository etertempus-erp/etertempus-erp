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
        result = None
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            result = db.execute(text(statement), params or {})
        db.commit()
        return result


def create_fixture() -> dict:
    organization_id = str(uuid4())
    category_id = str(uuid4())
    payment_id = str(uuid4())
    resource_id = str(uuid4())
    db_execute(
        """
        insert into organizations (id, name) values (:organization_id, :name);
        insert into expense_categories (id, organization_id, name, source)
        values (:category_id, :organization_id, 'Transporte', 'test');
        insert into payment_methods (id, organization_id, name)
        values (:payment_id, :organization_id, 'Efectivo');
        insert into resources (id, organization_id, code, name, type, unit)
        values (:resource_id, :organization_id, 'MP-GASTO-1', 'Cedron gasto test', 'raw_material', 'g');
        insert into inventory_movements (organization_id, resource_id, type, quantity, unit, reason)
        values (:organization_id, :resource_id, 'adjustment', 100, 'g', 'Stock inicial test');
        """,
        {
            "organization_id": organization_id,
            "name": f"Org gastos {organization_id}",
            "category_id": category_id,
            "payment_id": payment_id,
            "resource_id": resource_id,
        },
    )
    return {
        "organization_id": organization_id,
        "category_id": category_id,
        "payment_id": payment_id,
        "resource_id": resource_id,
    }


def cleanup_fixture(organization_id: str):
    db_execute(
        """
        delete from expenses where organization_id = :organization_id;
        delete from imported_expenses where organization_id = :organization_id;
        delete from inventory_movements where organization_id = :organization_id;
        delete from resources where organization_id = :organization_id;
        delete from payment_methods where organization_id = :organization_id;
        delete from expense_categories where organization_id = :organization_id;
        delete from organizations where id = :organization_id;
        """,
        {"organization_id": organization_id},
    )


def expense_payload(fixture: dict, amount: Decimal | float | int = 250) -> dict:
    return {
        "organization_id": fixture["organization_id"],
        "expense_date": "2026-07-27",
        "category_id": fixture["category_id"],
        "description": "Taxi para feria",
        "amount": float(amount),
        "payment_method_id": fixture["payment_id"],
        "supplier_name": "Taxi",
        "receipt_number": "G-001",
        "notes": "Prueba de gasto",
    }


def stock_for(fixture: dict):
    return db_scalar(
        """
        select coalesce(sum(quantity), 0)
        from inventory_movements
        where organization_id = :org and resource_id = :resource
        """,
        {"org": fixture["organization_id"], "resource": fixture["resource_id"]},
    )


def movement_count(fixture: dict):
    return db_scalar(
        "select count(*) from inventory_movements where organization_id = :org",
        {"org": fixture["organization_id"]},
    )


def test_create_expense_does_not_change_stock_or_inventory_movements():
    fixture = create_fixture()
    try:
        before_stock = stock_for(fixture)
        before_movements = movement_count(fixture)

        response = client.post("/expenses", json=expense_payload(fixture))
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "confirmed"
        assert body["origin"] == "system"
        assert body["amount"] == "250.00"

        assert stock_for(fixture) == before_stock
        assert movement_count(fixture) == before_movements
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_reject_zero_and_negative_expense_amounts():
    fixture = create_fixture()
    try:
        for amount in [0, -10]:
            response = client.post("/expenses", json=expense_payload(fixture, amount))
            assert response.status_code == 422
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_list_expenses_filters_and_totals():
    fixture = create_fixture()
    try:
        client.post("/expenses", json=expense_payload(fixture, 250))
        payload = expense_payload(fixture, 100)
        payload["description"] = "Publicidad redes"
        payload["supplier_name"] = "Meta"
        response = client.post("/expenses", json=payload)
        assert response.status_code == 201

        listing = client.get(
            "/expenses",
            params={
                "organization_id": fixture["organization_id"],
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "category_id": fixture["category_id"],
                "q": "Taxi",
            },
        )
        assert listing.status_code == 200
        body = listing.json()
        assert body["count"] == 1
        assert body["total"] == "250.00"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_update_only_administrative_fields():
    fixture = create_fixture()
    try:
        expense = client.post("/expenses", json=expense_payload(fixture)).json()
        response = client.put(
            f"/expenses/{expense['id']}",
            json={
                "organization_id": fixture["organization_id"],
                "supplier_name": "Nuevo destinatario",
                "receipt_number": "G-002",
                "notes": "Observacion actualizada",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["amount"] == "250.00"
        assert body["supplier_name"] == "Nuevo destinatario"
        assert body["receipt_number"] == "G-002"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_expense_and_prevent_double_cancel_without_stock_change():
    fixture = create_fixture()
    try:
        before_stock = stock_for(fixture)
        before_movements = movement_count(fixture)
        expense = client.post("/expenses", json=expense_payload(fixture)).json()

        first = client.post(
            f"/expenses/{expense['id']}/cancel",
            json={"organization_id": fixture["organization_id"], "reason": "Carga duplicada"},
        )
        second = client.post(
            f"/expenses/{expense['id']}/cancel",
            json={"organization_id": fixture["organization_id"], "reason": "Repetido"},
        )

        assert first.status_code == 200
        assert first.json()["status"] == "cancelled"
        assert second.status_code == 422
        assert "ya estaba anulado" in second.json()["detail"]
        assert stock_for(fixture) == before_stock
        assert movement_count(fixture) == before_movements
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_imported_expenses_are_listed_separately_without_duplication():
    fixture = create_fixture()
    try:
        db_execute(
            """
            insert into imported_expenses (
              organization_id, expense_date, category_name, supplier_name,
              amount, payment_method, source_sheet, source_row, control_status
            )
            values (
              :org, '2026-07-10', 'Transporte', 'Historico', 80.50,
              'Efectivo', 'Hoja test', 8, 'ok'
            )
            """,
            {"org": fixture["organization_id"]},
        )
        response = client.get(
            "/expenses",
            params={"organization_id": fixture["organization_id"], "origin": "imported"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["origin"] == "imported"
        assert body["total"] == "80.50"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_expense_summary_compares_with_sales_same_period():
    fixture = create_fixture()
    try:
        client.post("/expenses", json=expense_payload(fixture, 250))
        summary = client.get(
            "/expenses/summary",
            params={"organization_id": fixture["organization_id"], "reference_date": "2026-07-27"},
        )
        assert summary.status_code == 200
        body = summary.json()
        assert body["month_total"] == "250.00"
        assert body["year_total"] == "250.00"
        assert body["top_category_name"] == "Transporte"
    finally:
        cleanup_fixture(fixture["organization_id"])
