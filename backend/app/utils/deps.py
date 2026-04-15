from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.utils.security import decode_token
from app.models.user import User, Role

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()
    if not user or user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    # 预加载角色权限
    if user.role_id:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        user._role = role_result.scalar_one_or_none()
    else:
        user._role = None
    return user


def require_permission(permission: str):
    """RBAC 权限依赖：检查当前用户是否拥有指定权限"""
    async def _check(user: User = Depends(get_current_user)):
        role = getattr(user, "_role", None)
        if not role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户未分配角色")
        permissions: List[str] = role.permissions or []
        if "*" in permissions or permission in permissions:
            return user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {permission}")
    return _check
