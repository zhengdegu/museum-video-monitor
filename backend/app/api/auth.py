import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User, Role
from app.schemas.auth import LoginRequest, TokenOut, UserCreate, UserUpdate, UserOut, RoleOut
from app.schemas.common import ok, fail
from app.utils.security import hash_password, verify_password, create_access_token
from app.utils.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["认证与用户"])

# 简单的基于 IP 的 Rate Limiting：5次/分钟
_login_attempts: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 5
_RATE_WINDOW = 60  # 秒


def _check_rate_limit(ip: str):
    now = time.time()
    attempts = _login_attempts[ip]
    # 清理过期记录
    _login_attempts[ip] = [t for t in attempts if now - t < _RATE_WINDOW]
    if not _login_attempts[ip]:
        del _login_attempts[ip]
        return
    if len(_login_attempts[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁，请稍后再试")
    _login_attempts[ip].append(now)


@router.post("/login")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != 1:
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return ok(data=TokenOut(access_token=token))


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return ok(data=UserOut.model_validate(user))


@router.post("/users")
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        real_name=body.real_name,
        role_id=body.role_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return ok(data=UserOut.model_validate(user))


@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(User).order_by(User.id.asc()))
    items = [UserOut.model_validate(u) for u in result.scalars().all()]
    return ok(data=items)


@router.put("/users/{user_id}")
async def update_user(user_id: int, body: UserUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return fail("用户不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(user, k, v)
    await db.flush()
    await db.refresh(user)
    return ok(data=UserOut.model_validate(user))


@router.get("/roles")
async def list_roles(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Role).order_by(Role.id.asc()))
    items = [RoleOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=items)
