from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoomCreate(BaseModel):
    name: str
    code: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: int = 1


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None


class RoomOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
