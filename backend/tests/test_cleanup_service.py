"""清理服务测试 — 测试 CleanupService 基本逻辑"""
import pytest

pytestmark = pytest.mark.asyncio


class TestCleanupService:

    def test_cleanup_service_init(self):
        """测试 CleanupService 初始化"""
        from app.services.cleanup_service import CleanupService
        svc = CleanupService()
        assert svc._task is None

    async def test_stop_when_not_started(self):
        """停止未启动的服务不应报错"""
        from app.services.cleanup_service import CleanupService
        svc = CleanupService()
        await svc.stop()  # 不应抛异常
