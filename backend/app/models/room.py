from sqlalchemy import Column, BigInteger, String, Text, SmallInteger, DateTime, func
from app.database import Base


class StorageRoom(Base):
    __tablename__ = "museum_storage_room"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="库房名称")
    code = Column(String(50), unique=True, comment="库房编号")
    location = Column(String(200), comment="位置")
    description = Column(Text, comment="描述")
    status = Column(SmallInteger, default=1, comment="1启用 0禁用")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
