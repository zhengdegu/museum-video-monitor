from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class RuleCreate(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    rule_config: Optional[Any] = None
    enabled: int = 1


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    rule_config: Optional[Any] = None
    enabled: Optional[int] = None


class RuleOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    rule_type: Optional[str] = None
    rule_config: Optional[Any] = None
    enabled: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RuleHitOut(BaseModel):
    id: int
    event_id: int
    rule_id: int
    hit_time: datetime
    confidence: Optional[float] = None
    evidence_snapshot: Optional[str] = None
    detail: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
