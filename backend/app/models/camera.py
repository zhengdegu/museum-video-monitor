from sqlalchemy import Column, BigInteger, String, Integer, SmallInteger, DateTime, ForeignKey, func
from app.database import Base


class Camera(Base):
    __tablename__ = "museum_camera"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    room_id = Column(BigInteger, ForeignKey("museum_storage_room.id"), nullable=False, comment="所属库房")
    name = Column(String(100), nullable=False, comment="摄像头名称")
    rtsp_url = Column(String(500), nullable=False, comment="RTSP拉流地址")
    segment_duration = Column(Integer, default=10800, comment="视频分段时长(秒)")
    status = Column(SmallInteger, default=1, comment="1在线 2离线 3拉流中")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
