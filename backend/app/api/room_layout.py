from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.room_layout import RoomLayout
from app.models.event import Event
from app.models.camera import Camera
from app.utils.deps import get_current_user
from app.schemas.common import ok

router = APIRouter(prefix="/rooms", tags=["库房布局"])


@router.get("/{room_id}/layout")
async def get_room_layout(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取库房布局"""
    result = await db.execute(
        select(RoomLayout).where(RoomLayout.room_id == room_id)
    )
    layout = result.scalar_one_or_none()
    if not layout:
        return ok(data=None)
    return ok(data={
        "id": layout.id,
        "room_id": layout.room_id,
        "width": layout.width,
        "height": layout.height,
        "background_image": layout.background_image,
        "layout_data": layout.layout_data,
        "created_at": layout.created_at.isoformat() if layout.created_at else None,
        "updated_at": layout.updated_at.isoformat() if layout.updated_at else None,
    })


@router.put("/{room_id}/layout")
async def save_room_layout(
    room_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """保存/更新库房布局"""
    result = await db.execute(
        select(RoomLayout).where(RoomLayout.room_id == room_id)
    )
    layout = result.scalar_one_or_none()

    if layout:
        layout.width = body.get("width", layout.width)
        layout.height = body.get("height", layout.height)
        layout.background_image = body.get("background_image", layout.background_image)
        layout.layout_data = body.get("layout_data", layout.layout_data)
    else:
        layout = RoomLayout(
            room_id=room_id,
            width=body.get("width", 1000),
            height=body.get("height", 800),
            background_image=body.get("background_image"),
            layout_data=body.get("layout_data", {}),
        )
        db.add(layout)

    await db.flush()
    await db.refresh(layout)
    return ok(data={
        "id": layout.id,
        "room_id": layout.room_id,
        "width": layout.width,
        "height": layout.height,
        "background_image": layout.background_image,
        "layout_data": layout.layout_data,
        "created_at": layout.created_at.isoformat() if layout.created_at else None,
        "updated_at": layout.updated_at.isoformat() if layout.updated_at else None,
    })


@router.get("/{room_id}/heatmap")
async def get_room_heatmap(
    room_id: int,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取事件热力图数据（基于事件的 camera_id 映射到坐标）"""
    since = datetime.now() - timedelta(hours=hours)

    # 按 camera_id 聚合事件数量
    result = await db.execute(
        select(
            Event.camera_id,
            func.count(Event.id).label("event_count"),
        )
        .where(Event.room_id == room_id)
        .where(Event.event_time >= since)
        .group_by(Event.camera_id)
    )
    camera_events = result.all()

    # 获取布局中摄像头坐标
    layout_result = await db.execute(
        select(RoomLayout).where(RoomLayout.room_id == room_id)
    )
    layout = layout_result.scalar_one_or_none()

    heatmap_points = []
    if layout and layout.layout_data:
        cameras_layout = layout.layout_data.get("cameras", [])
        camera_pos_map = {c["camera_id"]: (c["x"], c["y"]) for c in cameras_layout}

        for row in camera_events:
            camera_id = row[0]
            count = row[1]
            if camera_id in camera_pos_map:
                x, y = camera_pos_map[camera_id]
                heatmap_points.append({
                    "camera_id": camera_id,
                    "x": x,
                    "y": y,
                    "count": count,
                })

    return ok(data={"points": heatmap_points, "hours": hours})


@router.get("/{room_id}/live-status")
async def get_room_live_status(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取库房实时状态（各摄像头在线状态、最近事件、当前人数）"""
    cam_result = await db.execute(
        select(Camera).where(Camera.room_id == room_id)
    )
    cameras = cam_result.scalars().all()

    camera_statuses = []
    total_person_count = 0

    for cam in cameras:
        # 获取该摄像头最近一条事件
        event_result = await db.execute(
            select(Event)
            .where(Event.camera_id == cam.id)
            .order_by(Event.event_time.desc())
            .limit(1)
        )
        latest_event = event_result.scalar_one_or_none()

        # 最近5分钟内的人数
        five_min_ago = datetime.now() - timedelta(minutes=5)
        person_result = await db.execute(
            select(func.max(Event.person_count))
            .where(Event.camera_id == cam.id)
            .where(Event.event_time >= five_min_ago)
        )
        current_persons = person_result.scalar() or 0
        total_person_count += current_persons

        camera_statuses.append({
            "camera_id": cam.id,
            "camera_name": cam.name,
            "status": cam.status,
            "latest_event": {
                "id": latest_event.id,
                "event_type": latest_event.event_type,
                "event_time": latest_event.event_time.isoformat() if latest_event.event_time else None,
                "description": latest_event.description,
            } if latest_event else None,
            "current_person_count": current_persons,
        })

    return ok(data={
        "room_id": room_id,
        "cameras": camera_statuses,
        "total_cameras": len(cameras),
        "online_cameras": sum(1 for c in cameras if c.status == 1),
        "total_person_count": total_person_count,
    })
