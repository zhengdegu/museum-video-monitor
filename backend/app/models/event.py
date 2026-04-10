from sqlalchemy import Column, BigInteger, String, Integer, SmallInteger, Text, DateTime, ForeignKey, JSON, func
from app.database import Base


class Event(Base):
    __tablename__ = "museum_event"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_video_id = Column(BigInteger, ForeignKey("museum_source_video.id"), nullable=False)
    person_segment_id = Column(BigInteger, ForeignKey("museum_person_segment.id"))
    camera_id = Column(BigInteger, ForeignKey("museum_camera.id"), nullable=False)
    room_id = Column(BigInteger, ForeignKey("museum_storage_room.id"), nullable=False)
    event_time = Column(DateTime, nullable=False)
    event_type = Column(String(50), comment="事件类型")
    person_count = Column(Integer)
    description = Column(Text, comment="事件描述")
    evidence_frames = Column(JSON, comment="证据截图路径列表")
    ai_conclusion = Column(Text, comment="AI分析结论")
    created_at = Column(DateTime, server_default=func.now())


class EventAggregate(Base):
    __tablename__ = "museum_event_aggregate"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    room_id = Column(BigInteger, ForeignKey("museum_storage_room.id"), nullable=False)
    camera_id = Column(BigInteger, ForeignKey("museum_camera.id"), nullable=False)
    session_start = Column(DateTime, nullable=False)
    session_end = Column(DateTime, nullable=False)
    total_events = Column(Integer, default=0)
    rule_hits = Column(Integer, default=0)
    summary = Column(Text, comment="聚合摘要")
    risk_level = Column(SmallInteger, default=0, comment="0正常 1低风险 2中风险 3高风险")
    created_at = Column(DateTime, server_default=func.now())
