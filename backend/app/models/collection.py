from sqlalchemy import Column, BigInteger, String, Text, SmallInteger, DateTime, ForeignKey, func
from app.database import Base


class Collection(Base):
    __tablename__ = "museum_collection"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), unique=True)
    room_id = Column(BigInteger, ForeignKey("museum_storage_room.id"))
    category = Column(String(50))
    description = Column(Text)
    image_url = Column(String(500))
    status = Column(SmallInteger, default=1, comment="1在库 2出库 3展览中")
    created_at = Column(DateTime, server_default=func.now())
