"""AI 盘点 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.inventory_task import AiInventoryTask, AiInventoryResult, AiInventorySchedule
from app.models.collection import Collection
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user
from datetime import datetime, timedelta

router = APIRouter(prefix="/inventory-ai", tags=["AI盘点"])


@router.post("/trigger")
async def trigger_inventory(
    room_id: int = Query(..., description="库房ID"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """手动触发 AI 盘点"""
    from app.services.inventory_ai_service import inventory_ai_service
    task_id = await inventory_ai_service.trigger_inventory(room_id=room_id, trigger_type="manual")
    return ok(data={"task_id": task_id}, message="盘点任务已触发")


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    status: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """盘点任务列表"""
    query = select(AiInventoryTask)
    if room_id is not None:
        query = query.where(AiInventoryTask.room_id == room_id)
    if status is not None:
        query = query.where(AiInventoryTask.status == status)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = query.order_by(desc(AiInventoryTask.id)).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    tasks = result.scalars().all()

    items = []
    for t in tasks:
        items.append({
            "id": t.id,
            "room_id": t.room_id,
            "trigger_type": t.trigger_type,
            "status": t.status,
            "started_at": str(t.started_at) if t.started_at else None,
            "completed_at": str(t.completed_at) if t.completed_at else None,
            "total_items": t.total_items,
            "matched_items": t.matched_items,
            "missing_items": t.missing_items,
            "uncertain_items": t.uncertain_items,
            "error_message": t.error_message,
            "created_at": str(t.created_at) if t.created_at else None,
        })

    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """任务详情"""
    task = await db.get(AiInventoryTask, task_id)
    if not task:
        return fail("任务不存在", 404)

    # 获取结果
    result = await db.execute(
        select(AiInventoryResult).where(AiInventoryResult.task_id == task_id)
    )
    results = result.scalars().all()

    result_items = []
    for r in results:
        # 获取藏品名称
        coll = await db.get(Collection, r.collection_id)
        result_items.append({
            "id": r.id,
            "collection_id": r.collection_id,
            "collection_name": coll.name if coll else "unknown",
            "collection_code": coll.code if coll else "",
            "status": r.status,
            "confidence": r.confidence,
            "description": r.description,
            "frame_path": r.frame_path,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return ok(data={
        "id": task.id,
        "room_id": task.room_id,
        "trigger_type": task.trigger_type,
        "status": task.status,
        "started_at": str(task.started_at) if task.started_at else None,
        "completed_at": str(task.completed_at) if task.completed_at else None,
        "total_items": task.total_items,
        "matched_items": task.matched_items,
        "missing_items": task.missing_items,
        "uncertain_items": task.uncertain_items,
        "error_message": task.error_message,
        "created_at": str(task.created_at) if task.created_at else None,
        "results": result_items,
    })


@router.get("/tasks/{task_id}/results")
async def get_task_results(
    task_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """盘点结果列表"""
    query = select(AiInventoryResult).where(AiInventoryResult.task_id == task_id)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    results = result.scalars().all()

    items = []
    for r in results:
        coll = await db.get(Collection, r.collection_id)
        items.append({
            "id": r.id,
            "collection_id": r.collection_id,
            "collection_name": coll.name if coll else "unknown",
            "collection_code": coll.code if coll else "",
            "status": r.status,
            "confidence": r.confidence,
            "description": r.description,
            "frame_path": r.frame_path,
            "created_at": str(r.created_at) if r.created_at else None,
        })

    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/schedule")
async def get_schedules(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取定时配置"""
    result = await db.execute(select(AiInventorySchedule))
    schedules = result.scalars().all()

    items = []
    for s in schedules:
        items.append({
            "id": s.id,
            "room_id": s.room_id,
            "interval_hours": s.interval_hours,
            "enabled": s.enabled,
            "last_run_at": str(s.last_run_at) if s.last_run_at else None,
            "created_at": str(s.created_at) if s.created_at else None,
        })

    return ok(data=items)


@router.put("/schedule")
async def update_schedule(
    room_id: int = Query(...),
    interval_hours: int = Query(24, ge=1),
    enabled: int = Query(1),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """更新定时配置（不存在则创建）"""
    result = await db.execute(
        select(AiInventorySchedule).where(AiInventorySchedule.room_id == room_id)
    )
    schedule = result.scalar_one_or_none()

    if schedule:
        schedule.interval_hours = interval_hours
        schedule.enabled = enabled
    else:
        schedule = AiInventorySchedule(
            room_id=room_id,
            interval_hours=interval_hours,
            enabled=enabled,
        )
        db.add(schedule)

    await db.commit()
    await db.refresh(schedule)

    return ok(data={
        "id": schedule.id,
        "room_id": schedule.room_id,
        "interval_hours": schedule.interval_hours,
        "enabled": schedule.enabled,
        "last_run_at": str(schedule.last_run_at) if schedule.last_run_at else None,
    })


@router.get("/stats")
async def get_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """盘点统计"""
    since = datetime.now() - timedelta(days=days)

    # 最近完成的任务统计
    result = await db.execute(
        select(AiInventoryTask).where(
            AiInventoryTask.status == "completed",
            AiInventoryTask.completed_at >= since,
        ).order_by(desc(AiInventoryTask.completed_at))
    )
    tasks = result.scalars().all()

    total_items_sum = sum(t.total_items or 0 for t in tasks)
    matched_sum = sum(t.matched_items or 0 for t in tasks)
    missing_sum = sum(t.missing_items or 0 for t in tasks)

    present_rate = (matched_sum / total_items_sum * 100) if total_items_sum > 0 else 0

    # 最近一次盘点
    last_task = tasks[0] if tasks else None

    # 每日缺失趋势
    trend = []
    for t in tasks:
        trend.append({
            "date": str(t.completed_at.date()) if t.completed_at else "",
            "total": t.total_items or 0,
            "present": t.matched_items or 0,
            "missing": t.missing_items or 0,
            "uncertain": t.uncertain_items or 0,
        })

    return ok(data={
        "total_tasks": len(tasks),
        "total_items_checked": total_items_sum,
        "present_rate": round(present_rate, 1),
        "total_missing": missing_sum,
        "last_inventory_at": str(last_task.completed_at) if last_task else None,
        "trend": trend[:30],
    })
