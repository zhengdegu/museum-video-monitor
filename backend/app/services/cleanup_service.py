"""磁盘空间管理 — 定期清理已分析完成的视频文件"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import select

from app.config import settings

logger = logging.getLogger(__name__)


class CleanupService:

    def __init__(self):
        self._task: asyncio.Task | None = None

    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("视频清理服务已启动")

    async def stop(self):
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("视频清理服务已停止")

    async def _loop(self):
        while True:
            try:
                await self.cleanup()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"视频清理异常: {e}")
            await asyncio.sleep(3600)  # 每小时执行一次

    async def cleanup(self) -> int:
        """扫描已分析完成且超过保留时间的视频文件并删除，返回删除数量"""
        from app.database import async_session
        from app.models.video import SourceVideo

        cutoff = datetime.now() - timedelta(hours=settings.VIDEO_RETENTION_HOURS)
        removed = 0

        async with async_session() as db:
            result = await db.execute(
                select(SourceVideo).where(
                    SourceVideo.analysis_status == 2,
                    SourceVideo.start_time < cutoff,
                )
            )
            videos = result.scalars().all()

        for video in videos:
            path = video.local_path
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    removed += 1
                    logger.info(f"已清理视频文件: {path}")
                except OSError as e:
                    logger.warning(f"删除文件失败 {path}: {e}")

        if removed:
            logger.info(f"本次清理完成，共删除 {removed} 个文件")
        return removed


cleanup_service = CleanupService()
