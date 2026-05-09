"""实时视频预览服务 — 轻量 YOLO 推理 + WebSocket 推送"""
import asyncio
import logging
import os
import tempfile
import time
from datetime import datetime
from typing import Optional

import cv2

from app.config import settings

logger = logging.getLogger(__name__)


class LivePreviewSession:
    """单路摄像头的实时预览会话"""

    def __init__(self, camera_id: int, rtsp_url: str):
        self.camera_id = camera_id
        # 通过 MediaMTX 中转地址抓帧
        self.rtsp_url = f"{settings.MEDIAMTX_RTSP_URL}/cam{camera_id}"
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._latest_frame: Optional[bytes] = None

    async def start(self):
        """启动实时推理循环"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._inference_loop())
        logger.info(f"实时预览启动: camera_id={self.camera_id}")

    async def stop(self):
        """停止实时推理"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info(f"实时预览停止: camera_id={self.camera_id}")

    @property
    def latest_frame(self) -> Optional[bytes]:
        return self._latest_frame

    async def _inference_loop(self):
        """持续从 RTSP 抓帧 -> YOLO 推理 -> 推送结果"""
        from app.services.yolo_detector import yolo_detector

        frame_interval = 0.4  # ~2.5 fps
        tmp_dir = tempfile.mkdtemp(prefix=f"live_cam{self.camera_id}_")

        try:
            while self._running:
                frame_path = os.path.join(tmp_dir, f"frame_{int(time.time() * 1000)}.jpg")
                try:
                    # 使用 ffmpeg 从 RTSP 抓取单帧
                    success = await self._grab_frame(frame_path)
                    if not success:
                        await asyncio.sleep(1)
                        continue

                    # 读取帧数据用于 snapshot
                    with open(frame_path, "rb") as f:
                        self._latest_frame = f.read()

                    # YOLO 推理（在线程池中执行）
                    loop = asyncio.get_event_loop()
                    detections = await loop.run_in_executor(
                        None, self._yolo_detect_sync, yolo_detector, frame_path
                    )

                    # 构造推送消息
                    message = {
                        "timestamp": datetime.now().isoformat(),
                        "person_count": len(detections),
                        "boxes": detections,
                        "frame_url": f"/api/v1/live/{self.camera_id}/snapshot",
                    }

                    # 非阻塞放入队列，满则丢弃旧数据
                    if self.queue.full():
                        try:
                            self.queue.get_nowait()
                        except asyncio.QueueEmpty:
                            pass
                    await self.queue.put(message)

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"实时预览推理异常 camera_id={self.camera_id}: {e}")
                    await asyncio.sleep(1)
                finally:
                    # 清理临时帧文件
                    if os.path.exists(frame_path):
                        try:
                            os.remove(frame_path)
                        except OSError:
                            pass

                await asyncio.sleep(frame_interval)
        finally:
            # 清理临时目录
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

    async def _grab_frame(self, output_path: str) -> bool:
        """使用 ffmpeg 从 RTSP 流抓取单帧 JPEG"""
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", self.rtsp_url,
            "-frames:v", "1",
            "-q:v", "2",
            output_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            return False

        return proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0

    @staticmethod
    def _yolo_detect_sync(detector, frame_path: str) -> list:
        """同步 YOLO 检测，返回人体检测框列表"""
        try:
            frame = cv2.imread(frame_path)
            if frame is None:
                return []
            result = detector.detect_frame(frame)
            boxes = []
            for det in result.get("boxes", []):
                bbox = det.get("bbox", [0, 0, 0, 0])
                boxes.append({
                    "x1": round(bbox[0], 1),
                    "y1": round(bbox[1], 1),
                    "x2": round(bbox[2], 1),
                    "y2": round(bbox[3], 1),
                    "confidence": round(det.get("confidence", 0), 3),
                    "label": "person",
                })
            return boxes
        except Exception as e:
            logger.error(f"YOLO 检测失败: {e}")
            return []


class LivePreviewManager:
    """管理所有摄像头的实时预览会话"""

    def __init__(self):
        self._sessions: dict[int, LivePreviewSession] = {}
        self._subscribers: dict[int, int] = {}  # camera_id -> 订阅者数量

    async def subscribe(self, camera_id: int, rtsp_url: str) -> LivePreviewSession:
        """订阅摄像头实时预览，返回会话对象"""
        if camera_id not in self._sessions:
            session = LivePreviewSession(camera_id, rtsp_url)
            self._sessions[camera_id] = session
            self._subscribers[camera_id] = 0
            await session.start()

        self._subscribers[camera_id] = self._subscribers.get(camera_id, 0) + 1
        return self._sessions[camera_id]

    async def unsubscribe(self, camera_id: int):
        """取消订阅，当无订阅者时停止推理"""
        count = self._subscribers.get(camera_id, 0) - 1
        self._subscribers[camera_id] = max(0, count)

        if count <= 0:
            session = self._sessions.pop(camera_id, None)
            self._subscribers.pop(camera_id, None)
            if session:
                await session.stop()

    def get_session(self, camera_id: int) -> Optional[LivePreviewSession]:
        """获取已有会话"""
        return self._sessions.get(camera_id)

    def is_active(self, camera_id: int) -> bool:
        return camera_id in self._sessions


# 全局单例
live_preview_manager = LivePreviewManager()
