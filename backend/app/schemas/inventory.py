from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class InventoryCheckCreate(BaseModel):
    room_id: int
    check_date: date
    total_count: int = 0
    checked_count: int = 0
    matched_count: int = 0
    mismatched_count: int = 0
    status: int = 0
    operator: Optional[str] = None
    remark: Optional[str] = None


class InventoryCheckUpdate(BaseModel):
    checked_count: Optional[int] = None
    matched_count: Optional[int] = None
    mismatched_count: Optional[int] = None
    status: Optional[int] = None
    remark: Optional[str] = None


class InventoryCheckOut(BaseModel):
    id: int
    room_id: int
    check_date: date
    total_count: int
    checked_count: int
    matched_count: int
    mismatched_count: int
    status: int
    operator: Optional[str] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MovementCreate(BaseModel):
    collection_id: int
    room_id: Optional[int] = None
    movement_type: int
    reason: Optional[str] = None
    operator: Optional[str] = None


class MovementOut(BaseModel):
    id: int
    collection_id: int
    room_id: Optional[int] = None
    movement_type: int
    reason: Optional[str] = None
    operator: Optional[str] = None
    moved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
