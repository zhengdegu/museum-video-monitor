"""AI 盘点定时调度器"""
import asyncio
import logging
from datetime import datetime
from typing import Dict

from sqlalchemy import select

from app.database import async_session
from app.models.inventory_task import AiInventorySchedule

logger = logging.getLogger(__name__)


class InventoryScheduler:
    """简单的 asyncio 定时器，按配置的间隔执行 AI 盘点"""

    def __init__(self):
        self._task: asyncio.Task = None
        self._running = False

    async def start(self):
        """启动调度器"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("AI 盘点调度器已启动")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AI 盘点调度器已停止")

    async def _loop(self):
        """主循环：每60秒检查一次是否有需要执行的定时盘点"""
        while self._running:
            try:
                await self._check_and_run()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"调度器检查异常: {e}")
            await asyncio.sleep(60)

    async def _check_and_run(self):
        """检查所有启用的定时配置，判断是否到期执行"""
        async with async_session() as db:
            result = await db.execute(
                select(AiInventorySchedule).where(AiInventorySchedule.enabled == 1)
            )
            schedules = result.scalars().all()

        now = datetime.now()

        for schedule in schedules:
            should_run = False
            if schedule.last_run_at is None:
                should_run = True
            else:
                elapsed_hours = (now - schedule.last_run_at).total_seconds() / 3600
                if elapsed_hours >= schedule.interval_hours:
                    should_run = True

            if should_run:
                logger.info(f"定时盘点触发: room_id={schedule.room_id}")
                from app.services.inventory_ai_service import inventory_ai_service
                try:
                    await inventory_ai_service.trigger_inventory(
                        room_id=schedule.room_id,
                        trigger_type="scheduled"
                    )
                    # 更新 last_run_at
                    async with async_session() as db:
                        sched = await db.get(AiInventorySchedule, schedule.id)
                        if sched:
                            sched.last_run_at = now
                            await db.commit()
                except Exception as e:
                    logger.error(f"定时盘点执行失败 room_id={schedule.room_id}: {e}")


# 全局单例
inventory_scheduler = InventoryScheduler()
