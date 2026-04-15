from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate, CameraOut
from app.utils.deps import get_current_user
from app.utils.crud import CRUDBase

router = APIRouter(prefix="/cameras", tags=["摄像头管理"])
_crud = CRUDBase(Camera, CameraOut, "摄像头")


@router.get("")
async def list_cameras(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None, description="按库房筛选"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    filters = [Camera.room_id == room_id] if room_id else None
    return await _crud.list_items(db, page, size, filters)


@router.get("/{camera_id}")
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.get_item(db, camera_id)


@router.post("")
async def create_camera(body: CameraCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.create_item(db, body)


@router.put("/{camera_id}")
async def update_camera(camera_id: int, body: CameraUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.update_item(db, camera_id, body)


@router.delete("/{camera_id}")
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    return await _crud.delete_item(db, camera_id)
