"""API Key 管理路由"""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.utils.deps import get_current_user
from app.utils.api_key import generate_api_key, hash_api_key
from app.schemas.common import ok, fail

router = APIRouter(prefix="/api-keys", tags=["API Key 管理"])


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key_prefix: str
    status: int
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreateOut(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str


class ApiKeyUpdate(BaseModel):
    status: int


@router.post("")
async def create_api_key(
    body: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建新 API Key（返回明文 Key，仅此一次）"""
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:8]

    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        status=1,
    )
    db.add(api_key)
    await db.flush()
    await db.refresh(api_key)

    return ok(data=ApiKeyCreateOut(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
    ))


@router.get("")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出当前用户的所有 API Key（不返回明文）"""
    result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.id.desc())
    )
    items = [ApiKeyOut.model_validate(k) for k in result.scalars().all()]
    return ok(data=items)


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除 API Key"""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    await db.delete(api_key)
    await db.flush()
    return ok(message="删除成功")


@router.patch("/{key_id}")
async def update_api_key(
    key_id: int,
    body: ApiKeyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """启用/禁用 API Key"""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="API Key 不存在")
    api_key.status = body.status
    await db.flush()
    await db.refresh(api_key)
    return ok(data=ApiKeyOut.model_validate(api_key))
