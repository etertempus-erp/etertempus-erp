from uuid import UUID

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    name: str
    role: str
    active: bool


class UserCreate(BaseModel):
    organization_id: UUID
    email: str
    name: str
    password: str = Field(min_length=8)
    role: str


class UserUpdate(BaseModel):
    name: str
    role: str
    active: bool
