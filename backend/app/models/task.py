from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.database import Base


class AnalysisTask(Base):
    __tablename__ = "analysis_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(Integer, ForeignKey("museum_source_video.id"), nullable=False)
    camera_id = Column(Integer, ForeignKey("museum_camera.id"), nullable=False)
    status = Column(String(20), default="pending", comment="pending/running/completed/failed")
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, comment="已重试次数")
