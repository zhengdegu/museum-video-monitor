"""推送渠道管理 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.push_channel import PushChannel, PushLog
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user
from app.services.push_service import push_service

router = APIRouter(prefix="/push-channels", tags=["推送渠道"])


@router.get("")
async def list_channels(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """获取所有推送渠道"""
    result = await db.execute(select(PushChannel).order_by(PushChannel.id))
    channels = result.scalars().all()
    items = [
        {
            "id": ch.id,
            "channel_type": ch.channel_type,
            "name": ch.name,
            "config": ch.config,
            "enabled": ch.enabled,
            "min_risk_level": ch.min_risk_level,
            "created_at": str(ch.created_at) if ch.created_at else None,
        }
        for ch in channels
    ]
    return ok(data=items)


@router.post("")
async def create_channel(
    data: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """新增推送渠道"""
    channel = PushChannel(
        channel_type=data.get("channel_type", ""),
        name=data.get("name", ""),
        config=data.get("config", {}),
        enabled=data.get("enabled", 1),
        min_risk_level=data.get("min_risk_level", 0),
    )
    if not channel.channel_type or not channel.name:
        return fail("channel_type 和 name 不能为空")
    if channel.channel_type not in ("feishu", "dingtalk", "email", "serverchan"):
        return fail("channel_type 必须为 feishu/dingtalk/email/serverchan")

    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return ok(data={"id": channel.id}, message="创建成功")


@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """编辑推送渠道"""
    result = await db.execute(select(PushChannel).where(PushChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        return fail("渠道不存在", 404)

    if "channel_type" in data:
        channel.channel_type = data["channel_type"]
    if "name" in data:
        channel.name = data["name"]
    if "config" in data:
        channel.config = data["config"]
    if "enabled" in data:
        channel.enabled = data["enabled"]
    if "min_risk_level" in data:
        channel.min_risk_level = data["min_risk_level"]

    await db.commit()
    return ok(message="更新成功")


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """删除推送渠道"""
    result = await db.execute(select(PushChannel).where(PushChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        return fail("渠道不存在", 404)

    await db.delete(channel)
    await db.commit()
    return ok(message="删除成功")


@router.post("/{channel_id}/test")
async def test_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """发送测试消息"""
    result = await db.execute(select(PushChannel).where(PushChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        return fail("渠道不存在", 404)

    success, response_text = await push_service.send_test(channel)
    if success:
        return ok(data={"response": response_text}, message="测试消息发送成功")
    else:
        return fail("测试消息发送失败: " + response_text)


@router.get("/logs")
async def list_push_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    channel_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    """查看推送日志"""
    query = select(PushLog)
    if channel_id is not None:
        query = query.where(PushLog.channel_id == channel_id)

    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0

    query = query.offset((page - 1) * size).limit(size).order_by(PushLog.sent_at.desc())
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [
        {
            "id": log.id,
            "channel_id": log.channel_id,
            "event_id": log.event_id,
            "status": log.status,
            "response": log.response,
            "sent_at": str(log.sent_at) if log.sent_at else None,
        }
        for log in logs
    ]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))
