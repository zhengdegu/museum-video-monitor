from sqlalchemy import Column, BigInteger, String, Integer, Float, Text, DateTime, ForeignKey, JSON, func
from app.database import Base


class PersonSegment(Base):
    __tablename__ = "museum_person_segment"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_video_id = Column(BigInteger, ForeignKey("museum_source_video.id"), nullable=False)
    start_time = Column(Float, nullable=False, comment="开始时间(秒)")
    end_time = Column(Float, nullable=False, comment="结束时间(秒)")
    person_count = Column(Integer, comment="检测到的人数(偏向值)")
    local_path = Column(String(500), comment="切片本地路径")
    created_at = Column(DateTime, server_default=func.now())


class VideoSegment(Base):
    __tablename__ = "museum_source_video_segment"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    person_segment_id = Column(BigInteger, ForeignKey("museum_person_segment.id"), nullable=False)
    segment_index = Column(Integer, nullable=False, comment="片段序号")
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    frame_count = Column(Integer, comment="抽帧数量")
    local_path = Column(String(500))
    analysis_result = Column(JSON, comment="大模型分析结论")
    merged_summary = Column(Text, comment="增量合并后的摘要")
    created_at = Column(DateTime, server_default=func.now())
