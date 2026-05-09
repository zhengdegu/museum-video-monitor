"""API Key 认证机制 — 通过 Header X-API-Key 认证，独立于 JWT"""
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db
from app.models.api_key import ApiKey
from app.models.user import User, Role
from app.utils.security import pwd_context


def generate_api_key() -> str:
    """生成 API Key（secrets.token_urlsafe(32)）"""
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """对 API Key 进行 bcrypt 哈希"""
    return pwd_context.hash(key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """验证 API Key"""
    return pwd_context.verify(plain_key, hashed_key)


async def get_user_by_api_key(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """通过 X-API-Key header 获取用户，用于开放 API 认证"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None

    # 用前缀快速筛选候选 Key
    prefix = api_key[:8]
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_prefix == prefix, ApiKey.status == 1)
    )
    candidates = result.scalars().all()

    matched_key: Optional[ApiKey] = None
    for candidate in candidates:
        if verify_api_key(api_key, candidate.key_hash):
            matched_key = candidate
            break

    if not matched_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
        )

    # 更新最后使用时间
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == matched_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.flush()

    # 获取关联用户
    user_result = await db.execute(
        select(User).where(User.id == matched_key.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user or user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 关联用户不存在或已禁用",
        )

    # 预加载角色
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        user._role = role_result.scalar_one_or_none()
    else:
        user._role = None

    return user


async def get_current_user_flexible(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """灵活认证：同时支持 JWT Bearer Token 和 X-API-Key 两种方式"""
    from app.utils.deps import get_current_user as jwt_get_user
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

    # 优先尝试 X-API-Key
    api_key_header = request.headers.get("X-API-Key")
    if api_key_header:
        user = await get_user_by_api_key(request, db)
        if user:
            return user

    # 回退到 JWT Bearer
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        from app.utils.security import decode_token
        token = auth_header[7:]
        payload = decode_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or user.status != 1:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
        if user.role_id:
            role_result = await db.execute(select(Role).where(Role.id == user.role_id))
            user._role = role_result.scalar_one_or_none()
        else:
            user._role = None
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="缺少认证凭据，请提供 Bearer Token 或 X-API-Key",
    )
