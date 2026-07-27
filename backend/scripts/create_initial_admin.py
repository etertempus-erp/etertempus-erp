from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import OrganizationModel, UserModel, UserRole
from app.db.session import SessionLocal

DEFAULT_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")


def main() -> None:
    if not settings.initial_admin_email or not settings.initial_admin_password:
        raise SystemExit(
            "Configura INITIAL_ADMIN_EMAIL e INITIAL_ADMIN_PASSWORD antes de crear el administrador."
        )
    if len(settings.initial_admin_password) < 12:
        raise SystemExit("INITIAL_ADMIN_PASSWORD debe tener al menos 12 caracteres para beta.")

    email = settings.initial_admin_email.strip().lower()
    with SessionLocal() as db:
        organization = db.get(OrganizationModel, DEFAULT_ORGANIZATION_ID)
        if organization is None:
            raise SystemExit("No existe la organizacion inicial. Aplica migraciones y seed antes de crear el admin.")

        existing = db.scalar(
            select(UserModel).where(UserModel.organization_id == organization.id, UserModel.email == email)
        )
        if existing:
            print("El administrador ya existe. No se modifico la contrasena.")
            return

        user = UserModel(
            organization_id=organization.id,
            email=email,
            name=settings.initial_admin_name.strip() or "Administrador",
            password_hash=hash_password(settings.initial_admin_password),
            role=UserRole.ADMIN,
            active=True,
        )
        db.add(user)
        db.commit()
        print(f"Administrador creado: {email}")


if __name__ == "__main__":
    main()
