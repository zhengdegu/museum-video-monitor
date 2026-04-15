"""认证相关接口测试：登录成功、登录失败、获取当前用户"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_login_success(client: AsyncClient, seed_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, seed_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert "密码错误" in resp.json()["detail"]


async def test_login_nonexistent_user(client: AsyncClient, seed_user):
    resp = await client.post("/api/v1/auth/login", json={"username": "nobody", "password": "any"})
    assert resp.status_code == 401


async def test_get_me_success(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"
    assert data["real_name"] == "测试管理员"


async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)
