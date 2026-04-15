from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.collection import Collection
from app.schemas.collection import CollectionCreate, CollectionUpdate, CollectionOut
from app.utils.deps import get_current_user
from app.utils.crud import CRUDBase

router = APIRouter(prefix="/collections", tags=["藏品管理"])
_crud = CRUDBase(Collection, CollectionOut, "藏品")


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
    filters = []
    if room_id:
        filters.append(Collection.room_id == room_id)
    if category:
        filters.append(Collection.category == category)
    if keyword:
        filters.append(Collection.name.contains(keyword))
    return await _crud.list_items(db, page, size, filters or None)


@router.get("/{coll_id}")
async def get_collection(coll_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.get_item(db, coll_id)


@router.post("")
async def create_collection(body: CollectionCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.create_item(db, body)


@router.put("/{coll_id}")
async def update_collection(coll_id: int, body: CollectionUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.update_item(db, coll_id, body)


@router.delete("/{coll_id}")
async def delete_collection(coll_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.delete_item(db, coll_id)
