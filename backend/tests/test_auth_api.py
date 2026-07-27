from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def db_execute(sql: str, params: dict | None = None):
    with SessionLocal() as db:
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            db.execute(text(statement), params or {})
        db.commit()


def create_user(role: str = "admin", active: bool = True) -> dict:
    organization_id = str(uuid4())
    user_id = str(uuid4())
    email = f"{role}-{user_id}@test.local"
    db_execute(
        """
        insert into organizations (id, name) values (:organization_id, :org_name);
        insert into users (id, organization_id, email, name, password_hash, role, active)
        values (:user_id, :organization_id, :email, :name, :password_hash, :role, :active);
        """,
        {
            "organization_id": organization_id,
            "org_name": f"Org auth {organization_id}",
            "user_id": user_id,
            "email": email,
            "name": "Usuario auth",
            "password_hash": hash_password("clave-segura-123"),
            "role": role,
            "active": active,
        },
    )
    return {"organization_id": organization_id, "user_id": user_id, "email": email, "password": "clave-segura-123"}


def cleanup(organization_id: str):
    db_execute(
        """
        delete from user_sessions where user_id in (select id from users where organization_id = :organization_id);
        delete from users where organization_id = :organization_id;
        delete from organizations where id = :organization_id;
        """,
        {"organization_id": organization_id},
    )


def login(email: str, password: str):
    local_client = TestClient(app)
    response = local_client.post("/auth/login", json={"email": email, "password": password})
    return local_client, response


def test_valid_login_and_me():
    fixture = create_user("admin")
    try:
        logged_client, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"
        me = logged_client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == fixture["email"]
    finally:
        cleanup(fixture["organization_id"])


def test_login_with_wrong_password_returns_401():
    fixture = create_user("admin")
    try:
        _, response = login(fixture["email"], "otra-clave")
        assert response.status_code == 401
    finally:
        cleanup(fixture["organization_id"])


def test_login_with_unknown_user_returns_401():
    response = client.post("/auth/login", json={"email": "nadie@test.local", "password": "clave-segura-123"})
    assert response.status_code == 401


def test_inactive_user_cannot_login():
    fixture = create_user("admin", active=False)
    try:
        _, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 401
    finally:
        cleanup(fixture["organization_id"])


def test_private_route_without_session_returns_401():
    fixture = create_user("admin")
    try:
        response = client.get(f"/dashboard/summary?organization_id={fixture['organization_id']}")
        assert response.status_code == 401
    finally:
        cleanup(fixture["organization_id"])


def test_logout_invalidates_session():
    fixture = create_user("admin")
    try:
        logged_client, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 200
        assert logged_client.post("/auth/logout").status_code == 200
        assert logged_client.get("/auth/me").status_code == 401
    finally:
        cleanup(fixture["organization_id"])


def test_viewer_can_read_but_cannot_create_resource():
    fixture = create_user("viewer")
    try:
        logged_client, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 200
        assert logged_client.get(f"/resources?organization_id={fixture['organization_id']}").status_code == 200
        create_response = logged_client.post(
            "/resources",
            json={
                "organization_id": fixture["organization_id"],
                "code": "MP-AUTH",
                "name": "Materia auth",
                "type": "raw_material",
                "unit": "g",
                "minimum_stock": 0,
            },
        )
        assert create_response.status_code == 403
    finally:
        cleanup(fixture["organization_id"])


def test_operator_cannot_cancel_purchase():
    fixture = create_user("operator")
    try:
        logged_client, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 200
        cancel_response = logged_client.post(
            f"/purchases/{uuid4()}/cancel?organization_id={fixture['organization_id']}",
            json={"reason": "Prueba de permisos"},
        )
        assert cancel_response.status_code == 403
    finally:
        cleanup(fixture["organization_id"])


def test_admin_can_access_user_management():
    fixture = create_user("admin")
    try:
        logged_client, response = login(fixture["email"], fixture["password"])
        assert response.status_code == 200
        users = logged_client.get(f"/users?organization_id={fixture['organization_id']}")
        assert users.status_code == 200
        assert users.json()[0]["role"] == "admin"
    finally:
        cleanup(fixture["organization_id"])


def test_cors_allowed_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejected_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "https://malicioso.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
