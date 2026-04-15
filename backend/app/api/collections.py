from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.collection import Collection
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/collections", tags=["藏品管理"])


@router.get("")
async def list_collections(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    category: str = Query(None),
    keyword: str = Query(""),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Collection)
    if room_id:
        query = query.where(Collection.room_id == room_id)
    if category:
        query = query.where(Collection.category == category)
    if keyword:
        query = query.where(Collection.name.contains(keyword))
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Collection.id.desc())
    result = await db.execute(query)
    items = [CollectionOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/{coll_id}")
async def get_collection(coll_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Collection).where(Collection.id == coll_id))
    coll = result.scalar_one_or_none()
    if not coll:
        return fail("藏品不存在", 404)
    return ok(data=CollectionOut.model_validate(coll))


@router.post("")
async def create_collection(body: CollectionCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    coll = Collection(**body.model_dump())
    db.add(coll)
    await db.flush()
    await db.refresh(coll)
    return ok(data=CollectionOut.model_validate(coll))


@router.put("/{coll_id}")
async def update_collection(coll_id: int, body: CollectionUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Collection).where(Collection.id == coll_id))
    coll = result.scalar_one_or_none()
    if not coll:
        return fail("藏品不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(coll, k, v)
    await db.flush()
    await db.refresh(coll)
    return ok(data=CollectionOut.model_validate(coll))


@router.delete("/{coll_id}")
async def delete_collection(coll_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Collection).where(Collection.id == coll_id))
    coll = result.scalar_one_or_none()
    if not coll:
        return fail("藏品不存在", 404)
    await db.delete(coll)
    return ok(message="删除成功")
