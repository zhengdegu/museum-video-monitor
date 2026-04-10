from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from app.database import get_db
from app.models.event import Event, EventAggregate
from app.models.room import StorageRoom
from app.models.rule import RuleHit
from app.schemas.event import EventOut, EventAggregateOut
from app.schemas.rule import RuleHitOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/events", tags=["事件中心"])


@router.get("")
async def list_events(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    camera_id: int = Query(None),
    event_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Event)
    if room_id is not None:
        query = query.where(Event.room_id == room_id)
    if camera_id is not None:
        query = query.where(Event.camera_id == camera_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Event.event_time.desc())
    result = await db.execute(query)
    items = [EventOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/aggregates")
async def list_aggregates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    risk_level: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(EventAggregate)
    if room_id is not None:
        query = query.where(EventAggregate.room_id == room_id)
    if risk_level is not None:
        query = query.where(EventAggregate.risk_level == risk_level)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(EventAggregate.session_start.desc())
    result = await db.execute(query)
    items = [EventAggregateOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/stats/trend")
async def event_trend(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    query = (
        select(cast(Event.event_time, Date).label("day"), func.count().label("count"))
        .where(Event.event_time >= since)
        .group_by(cast(Event.event_time, Date))
        .order_by(cast(Event.event_time, Date))
    )
    rows = (await db.execute(query)).all()
    # fill missing days with 0
    day_map = {str(r.day): r.count for r in rows}
    result = []
    for i in range(days):
        d = str(since + timedelta(days=i))
        result.append({"date": d, "count": day_map.get(d, 0)})
    return ok(data=result)


@router.get("/stats/room-risk")
async def room_risk(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    query = (
        select(EventAggregate.room_id, func.max(EventAggregate.risk_level).label("max_risk"))
        .group_by(EventAggregate.room_id)
    )
    rows = (await db.execute(query)).all()
    room_ids = [r.room_id for r in rows]
    risk_map = {r.room_id: r.max_risk for r in rows}

    rooms_q = select(StorageRoom).where(StorageRoom.id.in_(room_ids)) if room_ids else select(StorageRoom)
    rooms = (await db.execute(rooms_q)).scalars().all()
    result = [{"room_id": room.id, "room_name": room.name, "risk_level": risk_map.get(room.id, 0)} for room in rooms]
    result.sort(key=lambda x: x["risk_level"], reverse=True)
    return ok(data=result)


@router.get("/{event_id}")
async def get_event(event_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return fail("事件不存在", 404)
    return ok(data=EventOut.model_validate(event))


@router.get("/{event_id}/rule-hits")
async def get_event_rule_hits(event_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(RuleHit).where(RuleHit.event_id == event_id))
    items = [RuleHitOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=items)
