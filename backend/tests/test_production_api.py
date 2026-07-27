from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def db_execute(sql: str, params: dict | None = None):
    with SessionLocal() as db:
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            db.execute(text(statement), params or {})
        db.commit()


def create_fixture() -> dict:
    organization_id = str(uuid4())
    active_product_id = str(uuid4())
    inactive_product_id = str(uuid4())
    active_formula_id = str(uuid4())
    inactive_formula_id = str(uuid4())
    db_execute(
        """
        insert into organizations (id, name) values (:organization_id, :name);
        insert into resources (id, organization_id, code, name, type, unit, active)
        values
          (:active_product_id, :organization_id, 'PT-ACTIVO', 'Producto activo test', 'product', 'unit', true),
          (:inactive_product_id, :organization_id, 'PT-INACTIVO', 'Producto inactivo test', 'product', 'unit', false);
        insert into formulas (id, organization_id, product_resource_id, name, version, status, active_version)
        values
          (:active_formula_id, :organization_id, :active_product_id, 'Formula activo test', 1, 'active', true),
          (:inactive_formula_id, :organization_id, :inactive_product_id, 'Formula inactivo test', 1, 'active', true);
        """,
        {
            "organization_id": organization_id,
            "name": f"Org produccion {organization_id}",
            "active_product_id": active_product_id,
            "inactive_product_id": inactive_product_id,
            "active_formula_id": active_formula_id,
            "inactive_formula_id": inactive_formula_id,
        },
    )
    return {
        "organization_id": organization_id,
        "active_product_id": active_product_id,
        "inactive_product_id": inactive_product_id,
        "active_formula_id": active_formula_id,
        "inactive_formula_id": inactive_formula_id,
    }


def cleanup_fixture(organization_id: str):
    db_execute(
        """
        delete from inventory_movements where organization_id = :organization_id;
        delete from production_batches where organization_id = :organization_id;
        delete from formula_items where formula_id in (select id from formulas where organization_id = :organization_id);
        delete from formulas where organization_id = :organization_id;
        delete from resources where organization_id = :organization_id;
        delete from organizations where id = :organization_id;
        """,
        {"organization_id": organization_id},
    )


def test_cannot_create_batch_for_inactive_product():
    fixture = create_fixture()
    try:
        response = client.post(
            "/production/batches",
            json={
                "organization_id": fixture["organization_id"],
                "product_resource_id": fixture["inactive_product_id"],
                "formula_id": fixture["inactive_formula_id"],
                "elaboration_date": "2026-07-27",
                "target_weight": 100,
            },
        )
        assert response.status_code == 422
        assert "inactivo" in response.json()["detail"]
    finally:
        cleanup_fixture(fixture["organization_id"])


def test_cannot_create_batch_with_formula_from_another_product():
    fixture = create_fixture()
    try:
        response = client.post(
            "/production/batches",
            json={
                "organization_id": fixture["organization_id"],
                "product_resource_id": fixture["active_product_id"],
                "formula_id": fixture["inactive_formula_id"],
                "elaboration_date": "2026-07-27",
                "target_weight": 100,
            },
        )
        assert response.status_code == 422
        assert "no pertenece al producto" in response.json()["detail"]
    finally:
        cleanup_fixture(fixture["organization_id"])
