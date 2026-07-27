from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthenticatedUser(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    name: str
    role: str


class LoginResponse(BaseModel):
    user: AuthenticatedUser
    expires_at: datetime
