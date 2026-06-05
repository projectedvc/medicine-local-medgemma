from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import Role
from app.schemas.common import ORMModel


class UserCreate(BaseModel):
    login: str = Field(min_length=3, max_length=64)
    full_name: str = Field(min_length=2, max_length=160)
    role: Role
    password: str = Field(min_length=6, max_length=128)
    is_active: bool = True


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: Role | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    is_active: bool | None = None


class UserOut(ORMModel):
    id: int
    login: str
    full_name: str
    role: Role
    is_active: bool
    created_at: datetime
