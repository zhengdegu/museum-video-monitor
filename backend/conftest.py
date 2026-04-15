"""pytest 全局 fixtures — 内存 SQLite + httpx AsyncClient"""
import os

# 在任何 app 模块导入之前设置必要的环境变量
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")
os.environ.setdefault("MYSQL_USER", "test")
os.environ.setdefault("MYSQL_PASSWORD", "test")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
# 确保所有 model 都被导入，以便 create_all 能建表
import app.models  # noqa: F401
from app.utils.security import hash_password, create_access_token
from app.models.user import User, Role

# 内存 SQLite 异步引擎
TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """每个测试前重建所有表，测试后清理"""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    """提供一个独立的数据库 session"""
    async with TestSession() as session:
        yield session
        await session.commit()


@pytest_asyncio.fixture
async def client():
    """httpx AsyncClient，走 ASGI 直连"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_user(db: AsyncSession):
    """创建测试用户 admin/admin123，返回 User 对象"""
    role = Role(id=1, name="管理员", code="admin", permissions=["*"])
    db.add(role)
    await db.flush()

    user = User(
        id=1,
        username="admin",
        password_hash=hash_password("admin123"),
        real_name="测试管理员",
        role_id=1,
        status=1,
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def auth_headers(seed_user) -> dict:
    """返回带 Bearer token 的请求头"""
    token = create_access_token({"sub": str(seed_user.id), "username": seed_user.username})
    return {"Authorization": f"Bearer {token}"}
