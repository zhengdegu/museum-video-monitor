"""Agent 巡检服务 — 自动化监控、汇报、报警"""
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from sqlalchemy import select, func, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.event import Event, EventAggregate
from app.models.room import StorageRoom
from app.models.camera import Camera
from app.models.video import SourceVideo
from app.models.rule import Rule, RuleHit

logger = logging.getLogger(__name__)

RISK_EMOJI = {0: "✅", 1: "💛", 2: "⚠️", 3: "🔴"}
RISK_LABEL = {0: "正常", 1: "低风险", 2: "中风险", 3: "高风险"}


class AgentService:
    """博物馆安防 Agent — 巡检、汇报、报警"""

    # ── 数据采集 ──────────────────────────────────────────

    async def get_rooms(self) -> List[Dict]:
        async with async_session() as db:
            result = await db.execute(select(StorageRoom).order_by(StorageRoom.id))
            return [{"id": r.id, "name": r.name, "code": r.code, "status": r.status} for r in result.scalars().all()]

    async def get_cameras(self) -> List[Dict]:
        async with async_session() as db:
            result = await db.execute(select(Camera).order_by(Camera.id))
            return [{"id": c.id, "name": c.name, "room_id": c.room_id, "status": c.status} for c in result.scalars().all()]

    async def get_recent_events(self, hours: int = 24, limit: int = 20) -> List[Dict]:
        since = datetime.now() - timedelta(hours=hours)
        async with async_session() as db:
            result = await db.execute(
                select(Event)
                .where(Event.event_time >= since)
                .order_by(Event.event_time.desc())
                .limit(limit)
            )
            return [
                {
                    "id": e.id, "event_time": str(e.event_time)[:16],
                    "event_type": e.event_type, "room_id": e.room_id,
                    "camera_id": e.camera_id, "person_count": e.person_count,
                    "description": (e.description or "")[:100],
                    "ai_conclusion": (e.ai_conclusion or "")[:200],
                }
                for e in result.scalars().all()
            ]

    async def get_room_risk(self) -> List[Dict]:
        async with async_session() as db:
            agg_q = (
                select(EventAggregate.room_id, func.max(EventAggregate.risk_level).label("max_risk"))
                .group_by(EventAggregate.room_id)
            )
            rows = (await db.execute(agg_q)).all()
            risk_map = {r.room_id: r.max_risk for r in rows}

            rooms = (await db.execute(select(StorageRoom).order_by(StorageRoom.id))).scalars().all()
            return [
                {"room_id": room.id, "room_name": room.name, "risk_level": risk_map.get(room.id, 0)}
                for room in rooms
            ]

    async def get_event_trend(self, days: int = 7) -> List[Dict]:
        since = datetime.now().date() - timedelta(days=days - 1)
        async with async_session() as db:
            query = (
                select(cast(Event.event_time, Date).label("day"), func.count().label("count"))
                .where(Event.event_time >= since)
                .group_by(cast(Event.event_time, Date))
                .order_by(cast(Event.event_time, Date))
            )
            rows = (await db.execute(query)).all()
            day_map = {str(r.day): r.count for r in rows}
            return [
                {"date": str(since + timedelta(days=i)), "count": day_map.get(str(since + timedelta(days=i)), 0)}
                for i in range(days)
            ]

    async def get_rule_hit_stats(self) -> List[Dict]:
        async with async_session() as db:
            hit_q = select(RuleHit.rule_id, func.count().label("hit_count")).group_by(RuleHit.rule_id)
            rows = (await db.execute(hit_q)).all()
            hit_map = {r.rule_id: r.hit_count for r in rows}

            rules = (await db.execute(select(Rule).order_by(Rule.id))).scalars().all()
            return [
                {"rule_id": r.id, "rule_name": r.name, "code": r.code, "hit_count": hit_map.get(r.id, 0)}
                for r in rules
            ]

    async def get_analyzing_videos_count(self) -> int:
        async with async_session() as db:
            result = await db.execute(
                select(func.count()).select_from(SourceVideo).where(SourceVideo.analysis_status == 1)
            )
            return result.scalar() or 0

    async def get_violation_events(self, hours: int = 24) -> List[Dict]:
        """获取指定时间内的违规事件"""
        since = datetime.now() - timedelta(hours=hours)
        async with async_session() as db:
            result = await db.execute(
                select(Event)
                .where(Event.event_time >= since, Event.event_type == "violation")
                .order_by(Event.event_time.desc())
            )
            events = result.scalars().all()

            # 补充库房和摄像头名称
            room_ids = {e.room_id for e in events}
            cam_ids = {e.camera_id for e in events}

            rooms = {}
            if room_ids:
                r = await db.execute(select(StorageRoom).where(StorageRoom.id.in_(room_ids)))
                rooms = {rm.id: rm.name for rm in r.scalars().all()}

            cams = {}
            if cam_ids:
                c = await db.execute(select(Camera).where(Camera.id.in_(cam_ids)))
                cams = {cm.id: cm.name for cm in c.scalars().all()}

            return [
                {
                    "id": e.id,
                    "event_time": str(e.event_time)[:19],
                    "room_name": rooms.get(e.room_id, f"库房{e.room_id}"),
                    "camera_name": cams.get(e.camera_id, f"摄像头{e.camera_id}"),
                    "person_count": e.person_count,
                    "description": (e.description or "")[:200],
                    "ai_conclusion": (e.ai_conclusion or "")[:500],
                }
                for e in events
            ]

    # ── 报告生成 ──────────────────────────────────────────

    async def generate_patrol_report(self) -> str:
        """生成巡检报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [f"📊 博物馆安防巡检报告 ({now})", ""]

        try:
            # 库房风险
            risk_data = await self.get_room_risk()
            if risk_data:
                lines.append("🏠 库房状态:")
                for r in risk_data:
                    emoji = RISK_EMOJI.get(r["risk_level"], "❓")
                    label = RISK_LABEL.get(r["risk_level"], "未知")
                    lines.append(f"  - {r['room_name']}: {emoji} {label}")
                lines.append("")

            # 摄像头状态
            cameras = await self.get_cameras()
            if cameras:
                online = sum(1 for c in cameras if c["status"] == 1)
                total = len(cameras)
                offline = [c["name"] for c in cameras if c["status"] != 1]
                line = f"📹 摄像头: 在线 {online}/{total}"
                if offline:
                    line += f"，离线: {', '.join(offline)}"
                lines.append(line)
                lines.append("")

            # 正在分析的视频
            analyzing = await self.get_analyzing_videos_count()
            if analyzing > 0:
                lines.append(f"🔄 正在分析: {analyzing} 个视频")
                lines.append("")

            # 最近事件
            events = await self.get_recent_events(hours=24, limit=5)
            if events:
                lines.append("🔔 最近事件:")
                for e in events:
                    prefix = "🚨" if e["event_type"] == "violation" else "ℹ️"
                    desc = e["description"] or "无描述"
                    lines.append(f"  {prefix} [{e['event_time']}] {desc}")
                lines.append("")
            else:
                lines.append("🔔 最近24小时无事件")
                lines.append("")

            # 7日趋势
            trend = await self.get_event_trend(7)
            total_events = sum(d["count"] for d in trend)
            lines.append(f"📈 7日事件总数: {total_events}")
            lines.append("")

            # 规则命中
            rule_stats = await self.get_rule_hit_stats()
            hot_rules = [r for r in rule_stats if r["hit_count"] > 0]
            if hot_rules:
                hot_rules.sort(key=lambda x: x["hit_count"], reverse=True)
                lines.append("📋 规则命中 TOP:")
                for r in hot_rules[:5]:
                    lines.append(f"  - {r['rule_name']}: {r['hit_count']} 次")
                lines.append("")

            # 高风险提醒
            high_risk = [r for r in risk_data if r["risk_level"] >= 2]
            if high_risk:
                lines.append("⚠️ 需关注:")
                for r in high_risk:
                    lines.append(f"  - {r['room_name']} — {RISK_LABEL.get(r['risk_level'], '异常')}")

        except Exception as e:
            logger.error(f"生成巡检报告失败: {e}")
            lines.append(f"❌ 报告生成异常: {e}")

        return "\n".join(lines)

    async def generate_alert_messages(self, hours: int = 1) -> List[str]:
        """检查最近的违规事件，生成报警消息列表"""
        violations = await self.get_violation_events(hours=hours)
        messages = []
        for v in violations:
            msg = (
                f"🚨 博物馆安防报警\n"
                f"库房: {v['room_name']}\n"
                f"摄像头: {v['camera_name']}\n"
                f"时间: {v['event_time']}\n"
                f"AI分析: {v['ai_conclusion'][:300]}"
            )
            messages.append(msg)
        return messages

    async def generate_daily_report(self) -> str:
        """生成每日安防日报"""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [f"📋 博物馆安防日报 ({today})", "=" * 30, ""]

        try:
            # 今日事件统计
            events = await self.get_recent_events(hours=24, limit=100)
            total = len(events)
            violations = [e for e in events if e["event_type"] == "violation"]
            normals = [e for e in events if e["event_type"] != "violation"]

            lines.append(f"📊 今日事件统计:")
            lines.append(f"  - 总事件数: {total}")
            lines.append(f"  - 违规事件: {len(violations)}")
            lines.append(f"  - 正常事件: {len(normals)}")
            lines.append("")

            # 库房风险概览
            risk_data = await self.get_room_risk()
            if risk_data:
                lines.append("🏠 库房风险概览:")
                for r in risk_data:
                    emoji = RISK_EMOJI.get(r["risk_level"], "❓")
                    lines.append(f"  - {r['room_name']}: {emoji} {RISK_LABEL.get(r['risk_level'], '未知')}")
                lines.append("")

            # 违规事件详情
            if violations:
                lines.append("🚨 违规事件详情:")
                for i, v in enumerate(violations[:10], 1):
                    lines.append(f"  {i}. [{v['event_time']}] {v['description']}")
                if len(violations) > 10:
                    lines.append(f"  ... 还有 {len(violations) - 10} 条")
                lines.append("")

            # 规则命中排行
            rule_stats = await self.get_rule_hit_stats()
            hot = [r for r in rule_stats if r["hit_count"] > 0]
            if hot:
                hot.sort(key=lambda x: x["hit_count"], reverse=True)
                lines.append("📋 规则命中排行:")
                for r in hot[:5]:
                    lines.append(f"  - {r['rule_name']}: {r['hit_count']} 次")
                lines.append("")

            # 7日趋势
            trend = await self.get_event_trend(7)
            lines.append("📈 7日趋势:")
            for d in trend:
                bar = "█" * min(d["count"], 20)
                lines.append(f"  {d['date']}: {bar} {d['count']}")
            lines.append("")

            # 摄像头状态
            cameras = await self.get_cameras()
            if cameras:
                online = sum(1 for c in cameras if c["status"] == 1)
                offline = [c["name"] for c in cameras if c["status"] != 1]
                lines.append(f"📹 摄像头状态: 在线 {online}/{len(cameras)}")
                if offline:
                    lines.append(f"  ⚠️ 离线: {', '.join(offline)}")
                lines.append("")

            # 总结
            if violations:
                lines.append("📝 总结: 今日存在违规事件，请关注相关库房安全状况。")
            else:
                lines.append("📝 总结: 今日安防状况良好，无违规事件。")

        except Exception as e:
            logger.error(f"生成日报失败: {e}")
            lines.append(f"❌ 日报生成异常: {e}")

        return "\n".join(lines)

    async def health_summary(self) -> Dict:
        """系统健康状态汇总"""
        try:
            cameras = await self.get_cameras()
            rooms = await self.get_rooms()
            analyzing = await self.get_analyzing_videos_count()

            online_cams = sum(1 for c in cameras if c["status"] == 1)
            active_rooms = sum(1 for r in rooms if r["status"] == 1)

            return {
                "status": "healthy",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rooms": {"total": len(rooms), "active": active_rooms},
                "cameras": {"total": len(cameras), "online": online_cams},
                "analyzing_videos": analyzing,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# 全局单例
agent_service = AgentService()
