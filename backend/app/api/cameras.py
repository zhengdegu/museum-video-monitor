from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.camera import Camera
from app.schemas.camera import CameraCreate, CameraUpdate, CameraOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/cameras", tags=["摄像头管理"])


@router.get("")
async def list_cameras(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None, description="按库房筛选"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Camera)
    if room_id:
        query = query.where(Camera.room_id == room_id)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Camera.id.desc())
    result = await db.execute(query)
    items = [CameraOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/{camera_id}")
async def get_camera(camera_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        return fail("摄像头不存在", 404)
    return ok(data=CameraOut.model_validate(cam))


@router.post("")
async def create_camera(body: CameraCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    cam = Camera(**body.model_dump())
    db.add(cam)
    await db.flush()
    await db.refresh(cam)
    return ok(data=CameraOut.model_validate(cam))


@router.put("/{camera_id}")
async def update_camera(camera_id: int, body: CameraUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        return fail("摄像头不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(cam, k, v)
    await db.flush()
    await db.refresh(cam)
    return ok(data=CameraOut.model_validate(cam))


@router.delete("/{camera_id}")
async def delete_camera(camera_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Camera).where(Camera.id == camera_id))
    cam = result.scalar_one_or_none()
    if not cam:
        return fail("摄像头不存在", 404)
    await db.delete(cam)
    return ok(message="删除成功")
