from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CameraCreate(BaseModel):
    room_id: int
    name: str
    rtsp_url: str
    segment_duration: int = 10800


class CameraUpdate(BaseModel):
    room_id: Optional[int] = None
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    segment_duration: Optional[int] = None
    status: Optional[int] = None


class CameraOut(BaseModel):
    id: int
    room_id: int
    name: str
    rtsp_url: str
    segment_duration: int
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
