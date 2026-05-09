"""多馆管控 - 节点心跳服务"""
import asyncio
import logging
import platform
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.node import Node

logger = logging.getLogger(__name__)


class NodeService:
    """节点管理服务：作为管理中心接收心跳 / 作为本地节点上报心跳"""

    def __init__(self):
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ==================== 管理中心功能 ====================

    async def receive_heartbeat(self, api_key: str, data: dict, db: AsyncSession) -> bool:
        """接收节点心跳，更新节点状态"""
        result = await db.execute(
            select(Node).where(Node.api_key == api_key)
        )
        node = result.scalar_one_or_none()
        if not node:
            return False

        node.status = "online"
        node.version = data.get("version", "")
        node.last_heartbeat_at = datetime.now(timezone.utc)
        node.system_info = data.get("system_info")
        node.stats = data.get("stats")
        await db.flush()
        return True

    async def check_offline_nodes(self):
        """检测离线节点（超过 5 分钟无心跳 → offline）"""
        async with async_session() as db:
            threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
            await db.execute(
                update(Node)
                .where(Node.status == "online", Node.last_heartbeat_at < threshold)
                .values(status="offline")
            )
            await db.commit()

    async def get_overview(self, db: AsyncSession) -> dict:
        """全局概览统计"""
        result = await db.execute(select(Node))
        nodes = result.scalars().all()

        total = len(nodes)
        online = sum(1 for n in nodes if n.status == "online")
        offline = sum(1 for n in nodes if n.status == "offline")
        warning = sum(1 for n in nodes if n.status == "warning")

        total_events = 0
        total_warnings = 0
        total_cameras = 0
        total_cameras_online = 0
        for n in nodes:
            if n.stats:
                total_events += n.stats.get("events_today", 0)
                total_warnings += n.stats.get("warnings_active", 0)
                total_cameras += n.stats.get("cameras", 0)
                total_cameras_online += n.stats.get("cameras_online", 0)

        return {
            "total_nodes": total,
            "online": online,
            "offline": offline,
            "warning": warning,
            "total_events_today": total_events,
            "total_warnings_active": total_warnings,
            "total_cameras": total_cameras,
            "total_cameras_online": total_cameras_online,
        }

    # ==================== 本地节点功能 ====================

    async def _collect_local_stats(self) -> dict:
        """收集本地节点统计信息"""
        stats = {
            "cameras": 0,
            "cameras_online": 0,
            "events_today": 0,
            "warnings_active": 0,
            "disk_usage_pct": 0,
            "gpu_usage_pct": 0,
        }
        try:
            async with async_session() as db:
                from app.models.camera import Camera
                from app.models.event import Event
                from app.models.warning import Warning
                from sqlalchemy import func as sqlfunc

                # 摄像头统计
                cam_result = await db.execute(select(sqlfunc.count(Camera.id)))
                stats["cameras"] = cam_result.scalar() or 0

                cam_online_result = await db.execute(
                    select(sqlfunc.count(Camera.id)).where(Camera.status == 1)
                )
                stats["cameras_online"] = cam_online_result.scalar() or 0

                # 今日事件数
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                event_result = await db.execute(
                    select(sqlfunc.count(Event.id)).where(Event.created_at >= today_start)
                )
                stats["events_today"] = event_result.scalar() or 0

                # 活跃预警数
                warning_result = await db.execute(
                    select(sqlfunc.count(Warning.id)).where(Warning.status == "active")
                )
                stats["warnings_active"] = warning_result.scalar() or 0
        except Exception as e:
            logger.warning(f"收集本地统计失败: {e}")

        # 磁盘使用率
        try:
            import shutil
            total, used, free = shutil.disk_usage(".")
            stats["disk_usage_pct"] = round(used / total * 100, 1)
        except Exception:
            pass

        return stats

    def _collect_system_info(self) -> dict:
        """收集系统信息"""
        import os
        return {
            "os": f"{platform.system()} {platform.release()}",
            "cpu_cores": os.cpu_count() or 0,
            "python_version": platform.python_version(),
        }

    async def _send_heartbeat(self):
        """向中心端发送一次心跳"""
        if not settings.CENTER_URL or not settings.CENTER_API_KEY:
            return

        stats = await self._collect_local_stats()
        system_info = self._collect_system_info()

        payload = {
            "version": "1.0.0",
            "system_info": system_info,
            "stats": stats,
        }

        url = f"{settings.CENTER_URL.rstrip('/')}/api/v1/nodes/heartbeat"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json=payload,
                    headers={"X-Node-Key": settings.CENTER_API_KEY},
                )
                if resp.status_code != 200:
                    logger.warning(f"心跳上报失败: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"心跳上报异常: {e}")

    async def _heartbeat_loop(self):
        """心跳循环（每 60 秒）"""
        while True:
            try:
                await self._send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
            await asyncio.sleep(60)

    async def _offline_check_loop(self):
        """离线检测循环（每 60 秒，仅管理中心）"""
        while True:
            try:
                await self.check_offline_nodes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"离线检测异常: {e}")
            await asyncio.sleep(60)

    # ==================== 生命周期 ====================

    async def start(self):
        """根据角色启动对应任务"""
        if settings.NODE_ROLE == "node" and settings.CENTER_URL:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(f"节点心跳任务已启动，上报地址: {settings.CENTER_URL}")
        elif settings.NODE_ROLE == "center":
            self._heartbeat_task = asyncio.create_task(self._offline_check_loop())
            logger.info("管理中心离线检测任务已启动")

    async def stop(self):
        """停止任务"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None


node_service = NodeService()
