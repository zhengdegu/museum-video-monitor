from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.room import StorageRoom
from app.schemas.room import RoomCreate, RoomUpdate, RoomOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/rooms", tags=["库房管理"])


@router.get("")
async def list_rooms(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = Query("", description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(StorageRoom)
    if keyword:
        query = query.where(StorageRoom.name.contains(keyword))
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(StorageRoom.id.desc())
    result = await db.execute(query)
    items = [RoomOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/{room_id}")
async def get_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(StorageRoom).where(StorageRoom.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        return fail("库房不存在", 404)
    return ok(data=RoomOut.model_validate(room))


@router.post("")
async def create_room(body: RoomCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    room = StorageRoom(**body.model_dump())
    db.add(room)
    await db.flush()
    await db.refresh(room)
    return ok(data=RoomOut.model_validate(room))


@router.put("/{room_id}")
async def update_room(room_id: int, body: RoomUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(StorageRoom).where(StorageRoom.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        return fail("库房不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(room, k, v)
    await db.flush()
    await db.refresh(room)
    return ok(data=RoomOut.model_validate(room))


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(StorageRoom).where(StorageRoom.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        return fail("库房不存在", 404)
    await db.delete(room)
    return ok(message="删除成功")
