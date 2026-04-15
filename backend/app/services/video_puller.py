"""RTSP 视频拉流服务 — ffmpeg 切片 + 自动触发分析"""
import asyncio
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class VideoPuller:
    """使用 ffmpeg 从 RTSP 流按时间窗口切片，支持多路摄像头"""

    def __init__(self):
        self._tasks: dict[int, asyncio.Task] = {}

    async def start_all_cameras(self):
        """从数据库读取所有在线摄像头，启动拉流"""
        from app.database import async_session
        from app.models.camera import Camera
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(select(Camera).where(Camera.status == 1))
            cameras = result.scalars().all()

        if not cameras:
            logger.info("无在线摄像头，跳过拉流启动")
            return

        for cam in cameras:
            await self.start_pull(cam.id, cam.rtsp_url)
        logger.info(f"已启动 {len(cameras)} 路摄像头拉流")

    async def start_pull(self, camera_id: int, rtsp_url: str, segment_duration: int = 0, save_dir: Optional[str] = None):
        segment_duration = segment_duration or settings.RTSP_SEGMENT_DURATION
        save_dir = save_dir or settings.LOCAL_VIDEO_PATH
        os.makedirs(save_dir, exist_ok=True)

        if camera_id in self._tasks and not self._tasks[camera_id].done():
            logger.warning(f"摄像头 {camera_id} 已在拉流中")
            return

        task = asyncio.create_task(self._pull_loop(camera_id, rtsp_url, segment_duration, save_dir))
        self._tasks[camera_id] = task
        logger.info(f"开始拉流: camera_id={camera_id}, rtsp={rtsp_url}, segment={segment_duration}s")

    async def _pull_loop(self, camera_id: int, rtsp_url: str, segment_duration: int, save_dir: str):
        """持续拉流循环，每个切片完成后触发分析"""
        while True:
            try:
                filepath = await self._pull_one_segment(camera_id, rtsp_url, segment_duration, save_dir)
                if filepath and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                    await self._trigger_analysis(camera_id, filepath, segment_duration)
            except asyncio.CancelledError:
                logger.info(f"拉流任务取消: camera_id={camera_id}")
                return
            except Exception as e:
                logger.error(f"拉流异常 camera_id={camera_id}: {e}")
                await asyncio.sleep(5)

    async def _pull_one_segment(self, camera_id: int, rtsp_url: str, segment_duration: int, save_dir: str) -> Optional[str]:
        """使用 ffmpeg 拉取一个时间窗口的 RTSP 流"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cam{camera_id}_{timestamp}.mp4"
        filepath = os.path.join(save_dir, filename)

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-t", str(segment_duration),
            "-c", "copy",
            "-movflags", "+faststart",
            filepath,
        ]

        logger.info(f"ffmpeg 开始切片: camera_id={camera_id}, duration={segment_duration}s")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr.decode(errors="replace")[-500:] if stderr else "unknown"
            logger.error(f"ffmpeg 切片失败 camera_id={camera_id}: {err_msg}")
            # 清理空文件
            if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
                os.remove(filepath)
            return None

        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        logger.info(f"切片完成: {filepath}, size={file_size}")
        return filepath

    async def _trigger_analysis(self, camera_id: int, filepath: str, duration: int):
        """切片保存后写入 source_video 记录并触发分析任务"""
        from app.database import async_session
        from app.models.video import SourceVideo
        from app.models.camera import Camera
        from sqlalchemy import select

        async with async_session() as db:
            cam = await db.get(Camera, camera_id)
            room_id = cam.room_id if cam else 0

            video = SourceVideo(
                camera_id=camera_id,
                source_type=1,
                local_path=filepath,
                duration=duration,
                file_size=os.path.getsize(filepath),
                start_time=datetime.now(),
                analysis_status=0,
            )
            db.add(video)
            await db.commit()
            await db.refresh(video)
            video_id = video.id

        # 异步触发分析
        asyncio.create_task(self._run_analysis(video_id, filepath, camera_id, room_id))

    async def _run_analysis(self, video_id: int, filepath: str, camera_id: int, room_id: int):
        """调用视频分析器"""
        try:
            from app.services.video_analyzer import video_analyzer
            from app.database import async_session
            from app.models.rule import Rule
            from sqlalchemy import select

            async with async_session() as db:
                result = await db.execute(select(Rule).where(Rule.enabled == 1))
                rules = [
                    {"name": r.name, "code": r.code, "description": r.description, "enabled": 1}
                    for r in result.scalars().all()
                ]

            await video_analyzer.analyze(video_id, filepath, camera_id, room_id, rules)
        except Exception as e:
            logger.error(f"自动分析失败 video_id={video_id}: {e}")

    async def stop_pull(self, camera_id: int):
        task = self._tasks.pop(camera_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info(f"停止拉流: camera_id={camera_id}")

    async def stop_all(self):
        for camera_id in list(self._tasks.keys()):
            await self.stop_pull(camera_id)

    def is_pulling(self, camera_id: int) -> bool:
        return camera_id in self._tasks and not self._tasks[camera_id].done()


# 全局单例
video_puller = VideoPuller()
