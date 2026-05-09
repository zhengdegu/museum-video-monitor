from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class WarningOut(BaseModel):
    id: int
    camera_id: int
    room_id: int
    warning_type: str
    risk_score: int = 0
    person_track_id: Optional[str] = None
    trajectory_data: Optional[Any] = None
    description: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WarningRuleOut(BaseModel):
    id: int
    rule_type: str
    name: str
    config: Optional[Any] = None
    enabled: int = 1
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WarningRuleUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Any] = None
    enabled: Optional[int] = None
