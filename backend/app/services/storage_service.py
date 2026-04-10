"""文件存储服务 (本地 + MinIO)"""
import asyncio
import logging
import os
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """视频/截图存储：本地分析，完成后异步推送 MinIO"""

    def __init__(self):
        self._client: Optional[Minio] = None

    def _get_client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=False,
            )
            # 确保 bucket 存在
            if not self._client.bucket_exists(settings.MINIO_BUCKET):
                self._client.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"MinIO bucket 已创建: {settings.MINIO_BUCKET}")
        return self._client

    def upload_file(self, local_path: str, remote_key: str) -> str:
        """上传文件到 MinIO，返回访问 URL"""
        try:
            client = self._get_client()
            client.fput_object(settings.MINIO_BUCKET, remote_key, local_path)
            url = f"http://{settings.MINIO_ENDPOINT}/{settings.MINIO_BUCKET}/{remote_key}"
            logger.info(f"上传成功: {local_path} → {remote_key}")
            return url
        except S3Error as e:
            logger.error(f"MinIO 上传失败: {e}")
            raise

    async def async_push_video(self, video_id: int, local_path: str) -> Optional[str]:
        """异步推送已分析完成的视频到线上存储"""
        try:
            if not os.path.exists(local_path):
                logger.error(f"文件不存在: {local_path}")
                return None

            filename = os.path.basename(local_path)
            remote_key = f"videos/{video_id}/{filename}"
            url = await asyncio.to_thread(self.upload_file, local_path, remote_key)
            logger.info(f"视频已推送: video_id={video_id}, url={url}")
            return url
        except Exception as e:
            logger.error(f"视频推送失败 video_id={video_id}: {e}")
            return None

    async def push_frames(self, video_id: int, segment_index: int, frame_paths: list) -> list:
        """批量推送截图帧"""
        urls = []
        for fp in frame_paths:
            try:
                filename = os.path.basename(fp)
                remote_key = f"frames/{video_id}/seg{segment_index}/{filename}"
                url = await asyncio.to_thread(self.upload_file, fp, remote_key)
                urls.append(url)
            except Exception as e:
                logger.error(f"帧推送失败: {fp}, {e}")
        return urls


# 全局单例
storage_service = StorageService()
