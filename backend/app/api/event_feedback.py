"""事件确认/误报反馈 API"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.event import Event
from app.schemas.common import ok, fail
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/events", tags=["事件反馈"])


@router.post("/{event_id}/confirm")
async def confirm_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """确认事件"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return fail("事件不存在", 404)

    event.feedback_status = "confirmed"
    event.feedback_at = datetime.now()
    event.feedback_by = user.username
    await db.commit()
    return ok(message="事件已确认")


@router.post("/{event_id}/dismiss")
async def dismiss_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记事件为误报"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return fail("事件不存在", 404)

    event.feedback_status = "dismissed"
    event.feedback_at = datetime.now()
    event.feedback_by = user.username
    await db.commit()
    return ok(message="事件已标记为误报")


@router.get("/{event_id}/feedback")
async def get_event_feedback(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取事件反馈状态"""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        return fail("事件不存在", 404)

    return ok(data={
        "event_id": event.id,
        "feedback_status": event.feedback_status,
        "feedback_at": str(event.feedback_at) if event.feedback_at else None,
        "feedback_by": event.feedback_by,
    })
