"""清理服务测试：文件清理逻辑（mock 文件系统）"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.asyncio


class TestCleanupService:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        self.mock_db = AsyncMock()
        self.mock_session_ctx = AsyncMock()
        self.mock_session_ctx.__aenter__ = AsyncMock(return_value=self.mock_db)
        self.mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    def _make_video(self, vid, path, status=2, hours_ago=48):
        v = MagicMock()
        v.id = vid
        v.local_path = path
        v.analysis_status = status
        v.start_time = datetime.now() - timedelta(hours=hours_ago)
        return v

    async def test_cleanup_removes_old_analyzed_files(self):
        videos = [
            self._make_video(1, "/data/videos/cam1_old.mp4", status=2, hours_ago=48),
            self._make_video(2, "/data/videos/cam2_old.mp4", status=2, hours_ago=30),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = videos
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.cleanup_service.async_session", return_value=self.mock_session_ctx), \
             patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            from app.services.cleanup_service import CleanupService
            svc = CleanupService()
            removed = await svc.cleanup()
            assert removed == 2
            assert mock_remove.call_count == 2

    async def test_cleanup_skips_missing_files(self):
        videos = [self._make_video(1, "/data/videos/gone.mp4")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = videos
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.cleanup_service.async_session", return_value=self.mock_session_ctx), \
             patch("os.path.exists", return_value=False), \
             patch("os.remove") as mock_remove:
            from app.services.cleanup_service import CleanupService
            svc = CleanupService()
            removed = await svc.cleanup()
            assert removed == 0
            mock_remove.assert_not_called()

    async def test_cleanup_handles_oserror(self):
        videos = [self._make_video(1, "/data/videos/locked.mp4")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = videos
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.cleanup_service.async_session", return_value=self.mock_session_ctx), \
             patch("os.path.exists", return_value=True), \
             patch("os.remove", side_effect=OSError("permission denied")):
            from app.services.cleanup_service import CleanupService
            svc = CleanupService()
            removed = await svc.cleanup()
            assert removed == 0

    async def test_cleanup_returns_zero_when_nothing_to_clean(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.cleanup_service.async_session", return_value=self.mock_session_ctx):
            from app.services.cleanup_service import CleanupService
            svc = CleanupService()
            removed = await svc.cleanup()
            assert removed == 0

    async def test_cleanup_skips_none_path(self):
        videos = [self._make_video(1, None)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = videos
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.cleanup_service.async_session", return_value=self.mock_session_ctx), \
             patch("os.remove") as mock_remove:
            from app.services.cleanup_service import CleanupService
            svc = CleanupService()
            removed = await svc.cleanup()
            assert removed == 0
            mock_remove.assert_not_called()
