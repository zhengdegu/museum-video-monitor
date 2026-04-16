from sqlalchemy import Column, Integer, String, Text, SmallInteger, Date, DateTime, ForeignKey, func
from app.database import Base


class InventoryCheck(Base):
    __tablename__ = "museum_inventory_check"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(Integer, ForeignKey("museum_storage_room.id"), nullable=False)
    check_date = Column(Date, nullable=False)
    total_count = Column(Integer, default=0)
    checked_count = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    mismatched_count = Column(Integer, default=0)
    status = Column(SmallInteger, default=0, comment="0进行中 1已完成")
    operator = Column(String(50))
    remark = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class CollectionMovement(Base):
    __tablename__ = "museum_collection_movement"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("museum_collection.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("museum_storage_room.id"))
    movement_type = Column(SmallInteger, nullable=False, comment="1入库 2出库 3移库")
    reason = Column(String(200))
    operator = Column(String(50))
    moved_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, server_default=func.now())
