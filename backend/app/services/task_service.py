"""分析任务队列服务 — 创建/更新/重试"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update

from app.database import async_session
from app.models.task import AnalysisTask
from app.models.video import SourceVideo
from app.models.camera import Camera
from app.models.rule import Rule

logger = logging.getLogger(__name__)

MAX_RETRY = 3


class TaskService:

    async def create_task(self, video_id: int, camera_id: int) -> int:
        async with async_session() as db:
            task = AnalysisTask(video_id=video_id, camera_id=camera_id, status="pending")
            db.add(task)
            await db.commit()
            await db.refresh(task)
            logger.info(f"创建分析任务: task_id={task.id}, video_id={video_id}")
            return task.id

    async def mark_running(self, task_id: int):
        async with async_session() as db:
            await db.execute(
                update(AnalysisTask)
                .where(AnalysisTask.id == task_id)
                .values(status="running", started_at=datetime.now())
            )
            await db.commit()

    async def mark_completed(self, task_id: int):
        async with async_session() as db:
            await db.execute(
                update(AnalysisTask)
                .where(AnalysisTask.id == task_id)
                .values(status="completed", completed_at=datetime.now())
            )
            await db.commit()

    async def mark_failed(self, task_id: int, error: str):
        async with async_session() as db:
            result = await db.execute(select(AnalysisTask).where(AnalysisTask.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = error[:4000] if error else ""
                task.completed_at = datetime.now()
                task.retry_count = (task.retry_count or 0) + 1
                await db.commit()

    async def recover_stale_tasks(self):
        """启动时扫描 pending/running 任务，重新执行（最多重试3次）"""
        async with async_session() as db:
            result = await db.execute(
                select(AnalysisTask).where(
                    AnalysisTask.status.in_(["pending", "running"]),
                    AnalysisTask.retry_count < MAX_RETRY,
                )
            )
            tasks = result.scalars().all()

        if not tasks:
            logger.info("无需恢复的分析任务")
            return

        logger.info(f"恢复 {len(tasks)} 个未完成分析任务")
        for task in tasks:
            asyncio.create_task(self._execute_task(task.id, task.video_id, task.camera_id))

    async def _execute_task(self, task_id: int, video_id: int, camera_id: int):
        """执行单个分析任务"""
        try:
            await self.mark_running(task_id)

            async with async_session() as db:
                video = await db.get(SourceVideo, video_id)
                if not video or not video.local_path:
                    await self.mark_failed(task_id, "视频记录不存在或无本地路径")
                    return

                cam = await db.get(Camera, camera_id)
                room_id = cam.room_id if cam else 0

                rules_result = await db.execute(select(Rule).where(Rule.enabled == 1))
                rules = [
                    {"name": r.name, "code": r.code, "description": r.description, "enabled": 1}
                    for r in rules_result.scalars().all()
                ]

            from app.services.video_analyzer import video_analyzer
            await video_analyzer.analyze(video_id, video.local_path, camera_id, room_id, rules)
            await self.mark_completed(task_id)

        except Exception as e:
            logger.error(f"任务执行失败 task_id={task_id}: {e}")
            await self.mark_failed(task_id, str(e))


# 全局单例
task_service = TaskService()
