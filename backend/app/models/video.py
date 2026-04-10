from sqlalchemy import Column, BigInteger, String, Integer, SmallInteger, DateTime, ForeignKey, func
from app.database import Base


class SourceVideo(Base):
    __tablename__ = "museum_source_video"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(BigInteger, ForeignKey("museum_camera.id"), nullable=False)
    source_type = Column(SmallInteger, default=1, comment="1自动拉取 2手动上传")
    local_path = Column(String(500), comment="本地存储路径")
    remote_url = Column(String(500), comment="线上存储URL")
    duration = Column(Integer, comment="时长(秒)")
    file_size = Column(BigInteger, comment="文件大小(bytes)")
    start_time = Column(DateTime, comment="视频开始时间")
    end_time = Column(DateTime, comment="视频结束时间")
    analysis_status = Column(SmallInteger, default=0, comment="0待分析 1分析中 2已完成 3异常")
    upload_status = Column(SmallInteger, default=0, comment="0本地 1上传中 2已上传")
    created_at = Column(DateTime, server_default=func.now())
