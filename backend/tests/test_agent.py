"""Agent 巡检 API 测试"""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.room import StorageRoom
from app.models.camera import Camera
from app.models.event import Event, EventAggregate
from app.models.video import SourceVideo
from app.models.rule import Rule, RuleHit

pytestmark = pytest.mark.asyncio


# ── seed helpers ─────────────────────────────────────────


async def _seed_room(db: AsyncSession, **kw) -> StorageRoom:
    room = StorageRoom(name="一号库房", code="R001", status=1, **kw)
    db.add(room)
    await db.flush()
    return room


async def _seed_camera(db: AsyncSession, room_id: int, **kw) -> Camera:
    cam = Camera(name="摄像头A", rtsp_url="rtsp://fake", room_id=room_id, status=1, **kw)
    db.add(cam)
    await db.flush()
    return cam


async def _seed_video(db: AsyncSession, camera_id: int) -> SourceVideo:
    video = SourceVideo(camera_id=camera_id, analysis_status=1, source_type=1)
    db.add(video)
    await db.flush()
    return video


async def _seed_full(db: AsyncSession):
    """创建库房 + 摄像头 + 视频 + 事件 + 规则，返回所有对象"""
    room = await _seed_room(db)
    cam = await _seed_camera(db, room.id)
    video = await _seed_video(db, cam.id)

    now = datetime.now()
    event = Event(
        source_video_id=video.id,
        camera_id=cam.id,
        room_id=room.id,
        event_time=now - timedelta(hours=1),
        event_type="violation",
        person_count=2,
        description="有人员违规进入库房",
        ai_conclusion="AI检测到未授权人员进入",
    )
    db.add(event)
    await db.flush()

    normal_event = Event(
        source_video_id=video.id,
        camera_id=cam.id,
        room_id=room.id,
        event_time=now - timedelta(minutes=30),
        event_type="normal",
        person_count=1,
        description="正常巡检人员",
        ai_conclusion="正常活动",
    )
    db.add(normal_event)
    await db.flush()

    agg = EventAggregate(
        room_id=room.id,
        camera_id=cam.id,
        session_start=now - timedelta(hours=2),
        session_end=now,
        total_events=2,
        risk_level=2,
    )
    db.add(agg)

    rule = Rule(name="禁止单人进入", code="RULE001", rule_type="access")
    db.add(rule)
    await db.flush()

    hit = RuleHit(
        event_id=event.id,
        rule_id=rule.id,
        hit_time=now - timedelta(hours=1),
        confidence=0.95,
    )
    db.add(hit)
    await db.commit()

    return {"room": room, "camera": cam, "video": video, "event": event, "rule": rule}


# ── 认证测试 ─────────────────────────────────────────────


async def test_patrol_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/agent/patrol")
    assert resp.status_code in (401, 403)


async def test_alerts_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/agent/alerts")
    assert resp.status_code in (401, 403)


async def test_daily_report_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/agent/daily-report")
    assert resp.status_code in (401, 403)


async def test_health_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/agent/health")
    assert resp.status_code in (401, 403)


# ── 巡检报告 ─────────────────────────────────────────────


async def test_patrol_empty(client: AsyncClient, auth_headers, monkeypatch, db: AsyncSession):
    """无数据时巡检报告仍能正常返回"""
    _patch_agent_session(monkeypatch)
    resp = await client.get("/api/v1/agent/patrol", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert "report" in body["data"]
    assert "巡检报告" in body["data"]["report"]


async def test_patrol_with_data(client: AsyncClient, auth_headers, db: AsyncSession, monkeypatch):
    """有数据时巡检报告包含库房和事件信息"""
    _patch_agent_session(monkeypatch)
    await _seed_full(db)
    resp = await client.get("/api/v1/agent/patrol", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()["data"]["report"]
    assert "库房状态" in report
    assert "一号库房" in report
    assert "摄像头" in report


# ── 报警检测 ─────────────────────────────────────────────


async def test_alerts_empty(client: AsyncClient, auth_headers, monkeypatch, db: AsyncSession):
    """无违规事件时返回空列表"""
    _patch_agent_session(monkeypatch)
    resp = await client.get("/api/v1/agent/alerts", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] == 0
    assert data["alerts"] == []


async def test_alerts_with_violations(client: AsyncClient, auth_headers, db: AsyncSession, monkeypatch):
    """有违规事件时返回报警消息"""
    _patch_agent_session(monkeypatch)
    await _seed_full(db)
    resp = await client.get("/api/v1/agent/alerts", params={"hours": 24}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] >= 1
    assert "博物馆安防报警" in data["alerts"][0]


async def test_alerts_hours_param(client: AsyncClient, auth_headers, monkeypatch, db: AsyncSession):
    """hours 参数校验"""
    _patch_agent_session(monkeypatch)
    # 超出范围
    resp = await client.get("/api/v1/agent/alerts", params={"hours": 0}, headers=auth_headers)
    assert resp.status_code == 422

    resp = await client.get("/api/v1/agent/alerts", params={"hours": 100}, headers=auth_headers)
    assert resp.status_code == 422


# ── 日报 ─────────────────────────────────────────────────


async def test_daily_report_empty(client: AsyncClient, auth_headers, monkeypatch, db: AsyncSession):
    """无数据时日报仍能正常返回"""
    _patch_agent_session(monkeypatch)
    resp = await client.get("/api/v1/agent/daily-report", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    report = body["data"]["report"]
    assert "日报" in report
    assert "今日事件统计" in report


async def test_daily_report_with_data(client: AsyncClient, auth_headers, db: AsyncSession, monkeypatch):
    """有数据时日报包含违规详情"""
    _patch_agent_session(monkeypatch)
    await _seed_full(db)
    resp = await client.get("/api/v1/agent/daily-report", headers=auth_headers)
    assert resp.status_code == 200
    report = resp.json()["data"]["report"]
    assert "违规事件" in report
    assert "规则命中" in report


# ── 健康检查 ─────────────────────────────────────────────


async def test_health_empty(client: AsyncClient, auth_headers, monkeypatch, db: AsyncSession):
    """无数据时健康检查返回 healthy"""
    _patch_agent_session(monkeypatch)
    resp = await client.get("/api/v1/agent/health", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "healthy"
    assert data["rooms"]["total"] == 0
    assert data["cameras"]["total"] == 0


async def test_health_with_data(client: AsyncClient, auth_headers, db: AsyncSession, monkeypatch):
    """有数据时健康检查返回正确统计"""
    _patch_agent_session(monkeypatch)
    await _seed_full(db)
    resp = await client.get("/api/v1/agent/health", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "healthy"
    assert data["rooms"]["total"] == 1
    assert data["rooms"]["active"] == 1
    assert data["cameras"]["total"] == 1
    assert data["cameras"]["online"] == 1
    assert data["analyzing_videos"] == 1


# ── monkeypatch helper ───────────────────────────────────


def _patch_agent_session(monkeypatch):
    """将 agent_service 的 async_session 替换为测试用的 session factory"""
    from conftest import TestSession
    monkeypatch.setattr("app.services.agent_service.async_session", TestSession)
