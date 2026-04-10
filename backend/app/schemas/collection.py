from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CollectionCreate(BaseModel):
    name: str
    code: Optional[str] = None
    room_id: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    status: int = 1


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    room_id: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[int] = None


class CollectionOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    room_id: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
