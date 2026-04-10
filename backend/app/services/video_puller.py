"""RTSP 视频拉流服务"""
import asyncio
import logging
import os
import time
import threading
from datetime import datetime
from typing import Optional

import cv2

from app.config import settings

logger = logging.getLogger(__name__)


class VideoPuller:
    """多线程 RTSP 持续拉流，按配置时长自动切段保存"""

    def __init__(self):
        self._threads: dict[int, threading.Thread] = {}
        self._stop_flags: dict[int, threading.Event] = {}

    async def start_pull(self, camera_id: int, rtsp_url: str, segment_duration: int = 10800, save_dir: Optional[str] = None):
        save_dir = save_dir or settings.LOCAL_VIDEO_PATH
        os.makedirs(save_dir, exist_ok=True)

        if camera_id in self._threads and self._threads[camera_id].is_alive():
            logger.warning(f"摄像头 {camera_id} 已在拉流中")
            return

        stop_flag = threading.Event()
        self._stop_flags[camera_id] = stop_flag

        thread = threading.Thread(
            target=self._pull_loop,
            args=(camera_id, rtsp_url, segment_duration, save_dir, stop_flag),
            daemon=True,
        )
        thread.start()
        self._threads[camera_id] = thread
        logger.info(f"开始拉流: camera_id={camera_id}, rtsp={rtsp_url}")

    def _pull_loop(self, camera_id: int, rtsp_url: str, segment_duration: int, save_dir: str, stop_flag: threading.Event):
        while not stop_flag.is_set():
            try:
                self._pull_one_segment(camera_id, rtsp_url, segment_duration, save_dir, stop_flag)
            except Exception as e:
                logger.error(f"拉流异常 camera_id={camera_id}: {e}")
                if not stop_flag.is_set():
                    time.sleep(5)  # 异常后等5秒重试

    def _pull_one_segment(self, camera_id: int, rtsp_url: str, segment_duration: int, save_dir: str, stop_flag: threading.Event):
        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            logger.error(f"无法打开 RTSP 流: {rtsp_url}")
            time.sleep(10)
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cam{camera_id}_{timestamp}.mp4"
        filepath = os.path.join(save_dir, filename)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

        start_time = time.time()
        frame_count = 0
        logger.info(f"开始录制: {filepath}, fps={fps}, {width}x{height}")

        try:
            while not stop_flag.is_set():
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"读取帧失败 camera_id={camera_id}, 尝试重连")
                    break

                writer.write(frame)
                frame_count += 1

                elapsed = time.time() - start_time
                if elapsed >= segment_duration:
                    logger.info(f"分段完成: {filepath}, 帧数={frame_count}, 时长={elapsed:.0f}s")
                    break
        finally:
            writer.release()
            cap.release()

        if frame_count > 0:
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            duration = int(time.time() - start_time)
            logger.info(f"视频已保存: {filepath}, 大小={file_size}, 时长={duration}s")
            # TODO: 异步写入 museum_source_video 记录并触发分析

    async def stop_pull(self, camera_id: int):
        flag = self._stop_flags.pop(camera_id, None)
        if flag:
            flag.set()
        thread = self._threads.pop(camera_id, None)
        if thread:
            thread.join(timeout=10)
        logger.info(f"停止拉流: camera_id={camera_id}")

    def is_pulling(self, camera_id: int) -> bool:
        return camera_id in self._threads and self._threads[camera_id].is_alive()


# 全局单例
video_puller = VideoPuller()
