from concurrent.futures import ThreadPoolExecutor
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


def create_fixture(stock: Decimal = Decimal("10")) -> dict:
    organization_id = str(uuid4())
    product_id = str(uuid4())
    product_2_id = str(uuid4())
    channel_id = str(uuid4())
    payment_id = str(uuid4())
    point_id = str(uuid4())

    db_execute(
        """
        insert into organizations (id, name) values (:organization_id, :name);
        insert into resources (id, organization_id, code, name, type, unit)
        values
          (:product_id, :organization_id, 'P-TEST-1', 'Producto Test 1', 'product', 'unit'),
          (:product_2_id, :organization_id, 'P-TEST-2', 'Producto Test 2', 'product', 'unit');
        insert into inventory_movements (organization_id, resource_id, type, quantity, unit, reason)
        values
          (:organization_id, :product_id, 'adjustment', :stock, 'unit', 'Stock inicial test'),
          (:organization_id, :product_2_id, 'adjustment', :stock, 'unit', 'Stock inicial test');
        insert into sales_channels (id, organization_id, name)
        values (:channel_id, :organization_id, 'Venta directa');
        insert into payment_methods (id, organization_id, name)
        values (:payment_id, :organization_id, 'Efectivo');
        insert into points_of_sale (id, organization_id, name)
        values (:point_id, :organization_id, 'General');
        """,
        {
            "organization_id": organization_id,
            "name": f"Org test {organization_id}",
            "product_id": product_id,
            "product_2_id": product_2_id,
            "channel_id": channel_id,
            "payment_id": payment_id,
            "point_id": point_id,
            "stock": stock,
        },
    )
    return {
        "organization_id": organization_id,
        "product_id": product_id,
        "product_2_id": product_2_id,
        "channel_id": channel_id,
        "payment_id": payment_id,
        "point_id": point_id,
    }


def cleanup_fixture(organization_id: str):
    db_execute(
        """
        delete from sale_inventory_movements
        where sale_detail_id in (
          select id from sale_details where organization_id = :organization_id
        );
        delete from sale_details where organization_id = :organization_id;
        delete from sales where organization_id = :organization_id;
        delete from imported_sales where organization_id = :organization_id;
        delete from product_prices where organization_id = :organization_id;
        delete from inventory_movements where organization_id = :organization_id;
        delete from points_of_sale where organization_id = :organization_id;
        delete from payment_methods where organization_id = :organization_id;
        delete from sales_channels where organization_id = :organization_id;
        delete from resources where organization_id = :organization_id;
        delete from organizations where id = :organization_id;
        """,
        {"organization_id": organization_id},
    )


def sale_payload(fixture: dict, lines: list[dict] | None = None) -> dict:
    return {
        "organization_id": fixture["organization_id"],
        "sale_date": "2026-07-27",
        "channel_id": fixture["channel_id"],
        "payment_method_id": fixture["payment_id"],
        "customer_name": "Cliente test",
        "lines": lines
        or [
            {
                "product_resource_id": fixture["product_id"],
                "quantity": 2,
                "unit_price": 300,
                "discount": 0,
            }
        ],
    }


def test_create_valid_sale_with_one_product_decreases_stock():
    fixture = create_fixture()
    try:
        response = client.post("/sales", json=sale_payload(fixture))
        assert response.status_code == 201
        body = response.json()
        assert body["sale"]["status"] == "confirmed"
        assert body["sale"]["total"] == "600.00"
        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :product",
            {"org": fixture["organization_id"], "product": fixture["product_id"]},
        )
        assert stock == Decimal("8.000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_create_valid_sale_with_many_products():
    fixture = create_fixture()
    try:
        response = client.post(
            "/sales",
            json=sale_payload(
                fixture,
                [
                    {"product_resource_id": fixture["product_id"], "quantity": 1, "unit_price": 300, "discount": 0},
                    {"product_resource_id": fixture["product_2_id"], "quantity": 2, "unit_price": 250, "discount": 50},
                ],
            ),
        )
        assert response.status_code == 201
        assert response.json()["sale"]["total"] == "750.00"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_reject_sale_without_lines():
    fixture = create_fixture()
    try:
        payload = sale_payload(fixture)
        payload["lines"] = []
        response = client.post("/sales", json=payload)
        assert response.status_code == 422
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_reject_zero_and_negative_quantities_and_negative_price():
    fixture = create_fixture()
    try:
        for line in [
            {"product_resource_id": fixture["product_id"], "quantity": 0, "unit_price": 300, "discount": 0},
            {"product_resource_id": fixture["product_id"], "quantity": -1, "unit_price": 300, "discount": 0},
            {"product_resource_id": fixture["product_id"], "quantity": 1, "unit_price": -1, "discount": 0},
        ]:
            response = client.post("/sales", json=sale_payload(fixture, [line]))
            assert response.status_code == 422
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_reject_insufficient_stock_without_partial_sale_or_movement():
    fixture = create_fixture(stock=Decimal("1"))
    try:
        response = client.post("/sales", json=sale_payload(fixture))
        assert response.status_code == 409
        assert "Stock insuficiente" in response.json()["detail"]
        sales_count = db_scalar("select count(*) from sales where organization_id = :org", {"org": fixture["organization_id"]})
        movements_count = db_scalar(
            "select count(*) from inventory_movements where organization_id = :org and type = 'sale'",
            {"org": fixture["organization_id"]},
        )
        assert sales_count == 0
        assert movements_count == 0
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_sale_generates_inventory_movement_and_preserves_price():
    fixture = create_fixture()
    try:
        response = client.post("/sales", json=sale_payload(fixture))
        sale = response.json()["sale"]
        detail = client.get(f"/sales/{sale['id']}?organization_id={fixture['organization_id']}").json()
        assert len(detail["movements"]) == 1
        assert detail["movements"][0]["quantity"] == "-2.000"
        assert detail["lines"][0]["unit_price"] == "300.00"
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cancel_confirmed_sale_restores_stock():
    fixture = create_fixture()
    try:
        sale = client.post("/sales", json=sale_payload(fixture)).json()["sale"]
        response = client.post(
            f"/sales/{sale['id']}/cancel",
            json={"organization_id": fixture["organization_id"], "reason": "Error de carga"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :product",
            {"org": fixture["organization_id"], "product": fixture["product_id"]},
        )
        assert stock == Decimal("10.000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_confirmed_sale_cannot_be_edited_or_deleted():
    fixture = create_fixture()
    try:
        sale = client.post("/sales", json=sale_payload(fixture)).json()["sale"]
        assert client.put(f"/sales/{sale['id']}", json={}).status_code == 405
        assert client.delete(f"/sales/{sale['id']}").status_code == 405
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_imported_sales_are_listed_and_do_not_discount_stock():
    fixture = create_fixture()
    try:
        db_execute(
            """
            insert into imported_sales (
              organization_id, sale_date, channel_name, product_name, quantity,
              unit_price, total_amount, payment_method, source_sheet, source_row
            )
            values (:org, '2026-07-01', 'Venta directa', 'Producto Test 1', 1, 300, 300, 'Efectivo', 'Hoja test', 10)
            """,
            {"org": fixture["organization_id"]},
        )
        response = client.get(f"/sales?organization_id={fixture['organization_id']}&status=imported")
        assert response.status_code == 200
        assert response.json()[0]["source"] == "imported"
        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :product",
            {"org": fixture["organization_id"], "product": fixture["product_id"]},
        )
        assert stock == Decimal("10.000")
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_filter_sales_by_date_channel_and_product():
    fixture = create_fixture()
    try:
        client.post("/sales", json=sale_payload(fixture))
        response = client.get(
            "/sales",
            params={
                "organization_id": fixture["organization_id"],
                "date_from": "2026-07-01",
                "date_to": "2026-07-31",
                "channel_id": fixture["channel_id"],
                "product_resource_id": fixture["product_id"],
            },
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_two_concurrent_sales_cannot_consume_same_stock():
    fixture = create_fixture(stock=Decimal("1"))
    try:
        payload = sale_payload(
            fixture,
            [{"product_resource_id": fixture["product_id"], "quantity": 1, "unit_price": 300, "discount": 0}],
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post("/sales", json=payload), range(2)))
        statuses = sorted(response.status_code for response in responses)
        assert statuses == [201, 409]
        stock = db_scalar(
            "select coalesce(sum(quantity), 0) from inventory_movements where organization_id = :org and resource_id = :product",
            {"org": fixture["organization_id"], "product": fixture["product_id"]},
        )
        assert stock == Decimal("0.000")
    finally:
        cleanup_fixture(fixture["organization_id"])
