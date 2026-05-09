from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from app.database import get_db
from app.models.warning import Warning, WarningRule
from app.schemas.warning import WarningOut, WarningRuleOut, WarningRuleUpdate
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/warnings", tags=["预警中心"])


@router.get("")
async def list_warnings(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    camera_id: int = Query(None),
    warning_type: str = Query(None),
    status: str = Query(None),
    start_time: str = Query(None, description="开始时间 YYYY-MM-DD"),
    end_time: str = Query(None, description="结束时间 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Warning)
    if room_id is not None:
        query = query.where(Warning.room_id == room_id)
    if camera_id is not None:
        query = query.where(Warning.camera_id == camera_id)
    if warning_type:
        query = query.where(Warning.warning_type == warning_type)
    if status:
        query = query.where(Warning.status == status)
    if start_time:
        try:
            st = datetime.strptime(start_time, "%Y-%m-%d")
            query = query.where(Warning.created_at >= st)
        except ValueError:
            pass
    if end_time:
        try:
            et = datetime.strptime(end_time, "%Y-%m-%d")
            query = query.where(Warning.created_at <= et.replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Warning.risk_score.desc(), Warning.created_at.desc())
    result = await db.execute(query)
    items = [WarningOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/stats")
async def warning_stats(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """预警统计"""
    # 活跃预警数
    active_q = select(func.count()).where(Warning.status == "active")
    active_count = (await db.execute(active_q)).scalar() or 0

    # 今日新增
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = select(func.count()).where(Warning.created_at >= today)
    today_count = (await db.execute(today_q)).scalar() or 0

    # 已处理
    resolved_q = select(func.count()).where(Warning.status == "resolved")
    resolved_count = (await db.execute(resolved_q)).scalar() or 0

    # 误报数
    dismissed_q = select(func.count()).where(Warning.status == "dismissed")
    dismissed_count = (await db.execute(dismissed_q)).scalar() or 0

    # 误报率
    total_handled = resolved_count + dismissed_count
    false_alarm_rate = (dismissed_count / total_handled * 100) if total_handled > 0 else 0

    # 按类型统计
    type_q = select(Warning.warning_type, func.count().label("count")).where(
        Warning.status == "active"
    ).group_by(Warning.warning_type)
    type_rows = (await db.execute(type_q)).all()
    by_type = {r.warning_type: r.count for r in type_rows}

    # 按库房统计
    room_q = select(Warning.room_id, func.count().label("count")).where(
        Warning.status == "active"
    ).group_by(Warning.room_id)
    room_rows = (await db.execute(room_q)).all()
    by_room = {r.room_id: r.count for r in room_rows}

    return ok(data={
        "active_count": active_count,
        "today_count": today_count,
        "resolved_count": resolved_count,
        "dismissed_count": dismissed_count,
        "false_alarm_rate": round(false_alarm_rate, 1),
        "by_type": by_type,
        "by_room": by_room,
    })


@router.get("/{warning_id}")
async def get_warning(warning_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        return fail("预警不存在", 404)
    return ok(data=WarningOut.model_validate(warning))


@router.post("/{warning_id}/resolve")
async def resolve_warning(warning_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        return fail("预警不存在", 404)
    warning.status = "resolved"
    warning.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return ok(data=WarningOut.model_validate(warning))


@router.post("/{warning_id}/dismiss")
async def dismiss_warning(warning_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Warning).where(Warning.id == warning_id))
    warning = result.scalar_one_or_none()
    if not warning:
        return fail("预警不存在", 404)
    warning.status = "dismissed"
    warning.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return ok(data=WarningOut.model_validate(warning))


# ── 预警规则 ──────────────────────────────────────────

warning_rules_router = APIRouter(prefix="/warning-rules", tags=["预警规则"])


@warning_rules_router.get("")
async def list_warning_rules(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(WarningRule).order_by(WarningRule.id))
    items = [WarningRuleOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=items)


@warning_rules_router.put("/{rule_id}")
async def update_warning_rule(
    rule_id: int,
    body: WarningRuleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    result = await db.execute(select(WarningRule).where(WarningRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("规则不存在", 404)

    if body.name is not None:
        rule.name = body.name
    if body.config is not None:
        rule.config = body.config
    if body.enabled is not None:
        rule.enabled = body.enabled

    await db.commit()
    await db.refresh(rule)
    return ok(data=WarningRuleOut.model_validate(rule))
