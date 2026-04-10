from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    password: str
    real_name: Optional[str] = None
    role_id: Optional[int] = None


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    role_id: Optional[int] = None
    status: Optional[int] = None


class UserOut(BaseModel):
    id: int
    username: str
    real_name: Optional[str] = None
    role_id: Optional[int] = None
    status: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    permissions: Optional[list] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
