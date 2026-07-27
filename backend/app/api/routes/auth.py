from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import (
    clear_failed_logins,
    clear_session_cookie,
    current_user,
    login_attempt_key,
    record_failed_login,
    set_session_cookie,
    too_many_login_attempts,
    user_to_schema,
)
from app.core.config import settings
from app.core.security import create_session_token, session_expires_at, session_token_hash, verify_password
from app.db.models import UserModel, UserSessionModel
from app.db.session import get_db
from app.schemas.auth import AuthenticatedUser, LoginRequest, LoginResponse

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    attempt_key = login_attempt_key(request, email)
    if too_many_login_attempts(attempt_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Demasiados intentos. Espera unos minutos y vuelve a intentar.")

    user = db.scalar(select(UserModel).where(UserModel.email == email))
    if user is None or not user.active or not verify_password(payload.password, user.password_hash):
        record_failed_login(attempt_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email o contrasena incorrectos.")

    token = create_session_token()
    expires_at = session_expires_at()
    db.add(UserSessionModel(user_id=user.id, token_hash=session_token_hash(token), expires_at=expires_at))
    db.commit()
    clear_failed_logins(attempt_key)
    set_session_cookie(response, token, expires_at)
    return LoginResponse(user=user_to_schema(user), expires_at=expires_at)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        session = db.scalar(select(UserSessionModel).where(UserSessionModel.token_hash == session_token_hash(token)))
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=AuthenticatedUser)
def me(user: AuthenticatedUser = Depends(current_user)):
    return user
