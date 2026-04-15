"""库房 CRUD 接口测试"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ROOM_PAYLOAD = {"name": "一号库房", "code": "R001", "location": "A栋3层", "description": "青铜器库房"}


async def test_create_room(client: AsyncClient, auth_headers):
    resp = await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["name"] == "一号库房"
    assert data["code"] == "R001"
    assert data["id"] >= 1


async def test_list_rooms(client: AsyncClient, auth_headers):
    # 先创建两个
    await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    await client.post("/api/v1/rooms", json={**ROOM_PAYLOAD, "name": "二号库房", "code": "R002"}, headers=auth_headers)

    resp = await client.get("/api/v1/rooms", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()["data"]["items"]
    assert len(items) == 2


async def test_get_room(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    room_id = create_resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/rooms/{room_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "一号库房"


async def test_update_room(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    room_id = create_resp.json()["data"]["id"]

    resp = await client.put(f"/api/v1/rooms/{room_id}", json={"name": "改名库房"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["name"] == "改名库房"


async def test_delete_room(client: AsyncClient, auth_headers):
    create_resp = await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    room_id = create_resp.json()["data"]["id"]

    resp = await client.delete(f"/api/v1/rooms/{room_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["message"] == "删除成功"

    # 确认已删除
    resp = await client.get(f"/api/v1/rooms/{room_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_room_keyword_search(client: AsyncClient, auth_headers):
    await client.post("/api/v1/rooms", json=ROOM_PAYLOAD, headers=auth_headers)
    await client.post("/api/v1/rooms", json={**ROOM_PAYLOAD, "name": "书画库房", "code": "R003"}, headers=auth_headers)

    resp = await client.get("/api/v1/rooms", params={"keyword": "书画"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]["items"]) == 1


async def test_room_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/rooms")
    assert resp.status_code in (401, 403)
