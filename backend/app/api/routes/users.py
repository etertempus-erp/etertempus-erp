from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import require_roles
from app.core.security import hash_password
from app.db.models import UserModel, UserRole
from app.db.session import get_db
from app.schemas.users import UserCreate, UserRead, UserUpdate

router = APIRouter(dependencies=[Depends(require_roles(UserRole.ADMIN))])


def normalize_email(email: str) -> str:
    return email.strip().lower()


def parse_role(role: str) -> UserRole:
    try:
        return UserRole(role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Selecciona un rol valido.") from exc


def to_read(user: UserModel) -> UserRead:
    return UserRead(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        active=user.active,
    )


@router.get("", response_model=list[UserRead])
def list_users(organization_id: UUID = Query(...), db: Session = Depends(get_db)):
    users = db.scalars(
        select(UserModel)
        .where(UserModel.organization_id == organization_id)
        .order_by(UserModel.active.desc(), UserModel.name)
    ).all()
    return [to_read(user) for user in users]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=UserRead)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if not payload.email.strip():
        raise HTTPException(status_code=422, detail="El email es obligatorio.")
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio.")

    user = UserModel(
        organization_id=payload.organization_id,
        email=normalize_email(payload.email),
        name=payload.name.strip(),
        password_hash=hash_password(payload.password),
        role=parse_role(payload.role),
        active=True,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return to_read(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email.") from exc


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, organization_id: UUID = Query(...), db: Session = Depends(get_db)):
    user = db.get(UserModel, user_id)
    if user is None or user.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="El nombre es obligatorio.")

    user.name = payload.name.strip()
    user.role = parse_role(payload.role)
    user.active = payload.active
    db.commit()
    db.refresh(user)
    return to_read(user)
