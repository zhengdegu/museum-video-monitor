"""任务服务测试：创建任务、状态更新、重试逻辑"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

pytestmark = pytest.mark.asyncio


class TestTaskService:

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Mock 数据库会话和模型"""
        self.mock_db = AsyncMock()
        self.mock_session_ctx = AsyncMock()
        self.mock_session_ctx.__aenter__ = AsyncMock(return_value=self.mock_db)
        self.mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    def _make_service(self):
        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            return TaskService()

    async def test_create_task(self):
        mock_task = MagicMock()
        mock_task.id = 42

        self.mock_db.add = MagicMock()
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock(side_effect=lambda t: setattr(t, 'id', 42))

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            # patch AnalysisTask 构造
            with patch("app.services.task_service.AnalysisTask") as MockTask:
                MockTask.return_value = mock_task
                task_id = await svc.create_task(video_id=1, camera_id=2)
                assert task_id == 42
                self.mock_db.add.assert_called_once_with(mock_task)
                self.mock_db.commit.assert_awaited_once()

    async def test_mark_running(self):
        self.mock_db.execute = AsyncMock()
        self.mock_db.commit = AsyncMock()

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            await svc.mark_running(1)
            self.mock_db.execute.assert_awaited_once()
            self.mock_db.commit.assert_awaited_once()

    async def test_mark_completed(self):
        self.mock_db.execute = AsyncMock()
        self.mock_db.commit = AsyncMock()

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            await svc.mark_completed(1)
            self.mock_db.execute.assert_awaited_once()
            self.mock_db.commit.assert_awaited_once()

    async def test_mark_failed_increments_retry(self):
        mock_task = MagicMock()
        mock_task.retry_count = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.commit = AsyncMock()

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            await svc.mark_failed(1, "some error")
            assert mock_task.status == "failed"
            assert mock_task.retry_count == 1
            assert mock_task.error_message == "some error"

    async def test_mark_failed_truncates_long_error(self):
        mock_task = MagicMock()
        mock_task.retry_count = 2

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        self.mock_db.execute = AsyncMock(return_value=mock_result)
        self.mock_db.commit = AsyncMock()

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            long_error = "x" * 5000
            await svc.mark_failed(1, long_error)
            assert len(mock_task.error_message) == 4000

    async def test_recover_stale_tasks_skips_when_empty(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx):
            from app.services.task_service import TaskService
            svc = TaskService()
            # 不应抛异常
            await svc.recover_stale_tasks()

    async def test_recover_stale_tasks_creates_subtasks(self):
        mock_task = MagicMock()
        mock_task.id = 10
        mock_task.video_id = 20
        mock_task.camera_id = 30

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_task]
        self.mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.task_service.async_session", return_value=self.mock_session_ctx), \
             patch("asyncio.create_task") as mock_create_task:
            from app.services.task_service import TaskService
            svc = TaskService()
            await svc.recover_stale_tasks()
            mock_create_task.assert_called_once()
