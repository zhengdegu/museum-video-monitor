from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class VideoOut(BaseModel):
    id: int
    camera_id: int
    source_type: int
    local_path: Optional[str] = None
    remote_url: Optional[str] = None
    duration: Optional[int] = None
    file_size: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    analysis_status: int = 0
    upload_status: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventOut(BaseModel):
    id: int
    source_video_id: int
    person_segment_id: Optional[int] = None
    camera_id: int
    room_id: int
    event_time: datetime
    event_type: Optional[str] = None
    person_count: Optional[int] = None
    description: Optional[str] = None
    evidence_frames: Optional[List[str]] = None
    ai_conclusion: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EventAggregateOut(BaseModel):
    id: int
    room_id: int
    camera_id: int
    session_start: datetime
    session_end: datetime
    total_events: int = 0
    rule_hits: int = 0
    summary: Optional[str] = None
    risk_level: int = 0
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
