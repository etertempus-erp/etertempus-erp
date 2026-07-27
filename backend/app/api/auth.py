from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import session_token_hash
from app.db.models import UserModel, UserRole, UserSessionModel
from app.db.session import get_db
from app.schemas.auth import AuthenticatedUser

LOGIN_ATTEMPT_WINDOW = timedelta(minutes=15)
MAX_LOGIN_ATTEMPTS = 5
_login_attempts: dict[str, list[datetime]] = defaultdict(list)


def user_to_schema(user: UserModel) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        name=user.name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


def audit_user_id(user: AuthenticatedUser) -> UUID | None:
    if user.id.int == 0:
        return None
    return user.id


def record_failed_login(key: str) -> None:
    now = datetime.now(timezone.utc)
    recent = [item for item in _login_attempts[key] if now - item < LOGIN_ATTEMPT_WINDOW]
    recent.append(now)
    _login_attempts[key] = recent


def clear_failed_logins(key: str) -> None:
    _login_attempts.pop(key, None)


def too_many_login_attempts(key: str) -> bool:
    now = datetime.now(timezone.utc)
    recent = [item for item in _login_attempts[key] if now - item < LOGIN_ATTEMPT_WINDOW]
    _login_attempts[key] = recent
    return len(recent) >= MAX_LOGIN_ATTEMPTS


def login_attempt_key(request: Request, email: str) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{email.lower()}"


def current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if not settings.auth_required:
        return AuthenticatedUser(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            organization_id=UUID("00000000-0000-0000-0000-000000000001"),
            email="tests@eter.local",
            name="Usuario de pruebas",
            role=UserRole.ADMIN.value,
        )

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inicia sesion para continuar.")

    token_hash = session_token_hash(token)
    session = db.scalar(
        select(UserSessionModel).where(
            UserSessionModel.token_hash == token_hash,
            UserSessionModel.revoked_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    if session is None or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tu sesion vencio. Vuelve a iniciar sesion.")

    user = db.get(UserModel, session.user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El usuario ya no esta activo.")
    return user_to_schema(user)


def require_roles(*roles: UserRole):
    allowed = {role.value if hasattr(role, "value") else str(role) for role in roles}

    def dependency(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para realizar esta accion.")
        return user

    return dependency


def set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    max_age = max(int((expires_at - datetime.now(timezone.utc)).total_seconds()), 0)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/",
    )
