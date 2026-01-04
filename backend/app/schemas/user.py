import datetime
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Registration payload (AUTH-01)."""

    email: EmailStr
    password: str = Field(min_length=8)


class UserRead(BaseModel):
    """Public user representation — never exposes ``hashed_password``."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    created_at: datetime.datetime
