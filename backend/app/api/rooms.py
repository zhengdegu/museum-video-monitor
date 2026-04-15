from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.room import StorageRoom
from app.schemas.room import RoomCreate, RoomUpdate, RoomOut
from app.utils.deps import get_current_user
from app.utils.crud import CRUDBase

router = APIRouter(prefix="/rooms", tags=["库房管理"])
_crud = CRUDBase(StorageRoom, RoomOut, "库房")


@router.get("")
async def list_rooms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = [StorageRoom.name.contains(keyword)] if keyword else None
    return await _crud.list_items(db, page, size, filters)


@router.get("/{room_id}")
async def get_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.get_item(db, room_id)


@router.post("")
async def create_room(body: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.create_item(db, body)


@router.put("/{room_id}")
async def update_room(room_id: int, body: RoomUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.update_item(db, room_id, body)


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.delete_item(db, room_id)
