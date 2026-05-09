"""Webhook 管理路由"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.webhook import Webhook, WebhookLog
from app.models.user import User
from app.utils.deps import get_current_user
from app.services.webhook_service import webhook_service
from app.schemas.common import ok, fail

router = APIRouter(prefix="/webhooks", tags=["Webhook 管理"])


class WebhookCreate(BaseModel):
    url: str
    event_types: List[str]  # ["violation", "high_risk", "all"]


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    event_types: Optional[List[str]] = None
    status: Optional[int] = None


class WebhookOut(BaseModel):
    id: int
    url: str
    event_types: Optional[List[str]] = None
    status: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class WebhookCreateOut(BaseModel):
    id: int
    url: str
    secret: str
    event_types: List[str]


class WebhookLogOut(BaseModel):
    id: int
    webhook_id: int
    event_type: Optional[str] = None
    payload: Optional[dict] = None
    response_code: Optional[int] = None
    attempts: Optional[int] = None
    status: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.post("")
async def create_webhook(
    body: WebhookCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建 Webhook 订阅"""
    webhook_secret = secrets.token_urlsafe(32)
    webhook = Webhook(
        user_id=user.id,
        url=body.url,
        secret=webhook_secret,
        event_types=body.event_types,
        status=1,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)

    return ok(data=WebhookCreateOut(
        id=webhook.id,
        url=webhook.url,
        secret=webhook_secret,
        event_types=body.event_types,
    ))


@router.get("")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户的所有 Webhook"""
    result = await db.execute(
        select(Webhook).where(Webhook.user_id == user.id).order_by(Webhook.id.desc())
    )
    items = [WebhookOut.model_validate(w) for w in result.scalars().all()]
    return ok(data=items)


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单个 Webhook 详情"""
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    return ok(data=WebhookOut.model_validate(webhook))


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: int,
    body: WebhookUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新 Webhook"""
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook 不存在")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(webhook, field, value)
    await db.flush()
    await db.refresh(webhook)
    return ok(data=WebhookOut.model_validate(webhook))


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除 Webhook"""
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    await db.delete(webhook)
    await db.flush()
    return ok(message="删除成功")


@router.get("/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查看 Webhook 投递日志"""
    # 验证 webhook 归属
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook 不存在")

    log_result = await db.execute(
        select(WebhookLog)
        .where(WebhookLog.webhook_id == webhook_id)
        .order_by(WebhookLog.id.desc())
        .limit(100)
    )
    items = [WebhookLogOut.model_validate(log) for log in log_result.scalars().all()]
    return ok(data=items)


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """发送测试事件"""
    # 验证 webhook 归属
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Webhook 不存在")

    test_result = await webhook_service.send_test_event(webhook_id)
    return ok(data=test_result)
