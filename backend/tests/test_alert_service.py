"""报警推送服务测试：payload 构建、webhook 为空跳过、重试逻辑"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.services.alert_service import AlertService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def svc():
    return AlertService()


class TestBuildPayload:
    def test_feishu_payload(self, svc):
        payload = svc._build_feishu_payload("测试内容")
        assert payload["msg_type"] == "text"
        assert payload["content"]["text"] == "测试内容"

    def test_dingtalk_payload(self, svc):
        payload = svc._build_dingtalk_payload("测试内容")
        assert payload["msgtype"] == "text"
        assert payload["text"]["content"] == "测试内容"


class TestSendAlert:
    async def test_skip_when_no_webhook_url(self, svc):
        with patch("app.services.alert_service.settings") as mock_settings:
            mock_settings.ALERT_WEBHOOK_URL = ""
            result = await svc.send_alert(
                event_type="violation",
                room_name="一号库房",
                camera_name="cam1",
                risk_level=3,
                event_time=datetime(2025, 1, 1, 12, 0, 0),
                summary="测试",
            )
            assert result is False

    async def test_unsupported_webhook_type(self, svc):
        with patch("app.services.alert_service.settings") as mock_settings:
            mock_settings.ALERT_WEBHOOK_URL = "https://example.com/hook"
            mock_settings.ALERT_WEBHOOK_TYPE = "unknown_type"
            result = await svc.send_alert(
                event_type="alert",
                room_name="二号库房",
                camera_name="cam2",
                risk_level=2,
                event_time=datetime(2025, 1, 1),
                summary="test",
            )
            assert result is False

    async def test_success_on_first_try(self, svc):
        mock_resp = AsyncMock()
        mock_resp.raise_for_status = lambda: None

        with patch("app.services.alert_service.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
            mock_settings.ALERT_WEBHOOK_URL = "https://example.com/hook"
            mock_settings.ALERT_WEBHOOK_TYPE = "feishu"
            result = await svc.send_alert(
                event_type="violation",
                room_name="库房",
                camera_name="cam",
                risk_level=3,
                event_time=datetime(2025, 1, 1),
                summary="ok",
            )
            assert result is True
            assert mock_post.call_count == 1

    async def test_retry_on_failure(self, svc):
        with patch("app.services.alert_service.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", side_effect=Exception("网络错误")), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_settings.ALERT_WEBHOOK_URL = "https://example.com/hook"
            mock_settings.ALERT_WEBHOOK_TYPE = "dingtalk"
            result = await svc.send_alert(
                event_type="alert",
                room_name="库房",
                camera_name="cam",
                risk_level=2,
                event_time=datetime(2025, 1, 1),
                summary="fail",
            )
            assert result is False
            # 重试2次 sleep（第3次失败后不再 sleep）
            assert mock_sleep.call_count == 2
            # 指数退避: 1s, 2s
            mock_sleep.assert_any_call(1)
            mock_sleep.assert_any_call(2)
