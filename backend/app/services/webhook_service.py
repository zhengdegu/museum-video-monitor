"""Webhook 投递服务 — 异步推送事件到订阅的 Webhook URL"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select

from app.database import async_session
from app.models.webhook import Webhook, WebhookLog

logger = logging.getLogger(__name__)


class WebhookService:
    """管理 Webhook 事件投递"""

    @staticmethod
    def sign_payload(payload: Dict[str, Any], secret: str) -> str:
        """使用 HMAC-SHA256 签名 payload"""
        payload_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def dispatch_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """向所有匹配的 Webhook 订阅者投递事件"""
        async with async_session() as db:
            result = await db.execute(
                select(Webhook).where(Webhook.status == 1)
            )
            webhooks = result.scalars().all()

            for wh in webhooks:
                event_types: List[str] = wh.event_types or []
                if "all" not in event_types and event_type not in event_types:
                    continue
                asyncio.create_task(
                    self._deliver(wh.id, wh.url, wh.secret, event_type, payload)
                )

    async def _deliver(
        self,
        webhook_id: int,
        url: str,
        secret: str,
        event_type: str,
        payload: Dict[str, Any],
        max_retries: int = 3,
    ) -> None:
        """投递单个 Webhook，含重试机制（指数退避）"""
        signature = self.sign_payload(payload, secret)
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Webhook-Event": event_type,
            "X-Webhook-Timestamp": str(int(time.time())),
        }

        response_code: Optional[int] = None
        delivery_status = "failed"
        attempts = 0

        for attempt in range(max_retries):
            attempts = attempt + 1
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                    response_code = resp.status_code
                    if 200 <= resp.status_code < 300:
                        delivery_status = "success"
                        logger.info(f"Webhook 投递成功: webhook_id={webhook_id}, event={event_type}")
                        break
                    else:
                        logger.warning(
                            f"Webhook 投递失败(HTTP {resp.status_code}): webhook_id={webhook_id}, 第{attempts}次"
                        )
            except Exception as e:
                logger.warning(f"Webhook 投递异常: webhook_id={webhook_id}, 第{attempts}次, {e}")
                response_code = None

            if attempt < max_retries - 1:
                wait = 2 ** attempt
                await asyncio.sleep(wait)

        if delivery_status != "success":
            logger.error(f"Webhook 投递最终失败: webhook_id={webhook_id}, event={event_type}")

        # 记录投递日志
        async with async_session() as db:
            log = WebhookLog(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                response_code=response_code,
                attempts=attempts,
                status=delivery_status,
            )
            db.add(log)
            await db.commit()

    async def send_test_event(self, webhook_id: int) -> Dict[str, Any]:
        """发送测试事件到指定 Webhook"""
        async with async_session() as db:
            result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
            webhook = result.scalar_one_or_none()
            if not webhook:
                return {"success": False, "message": "Webhook 不存在"}

            test_payload = {
                "event_type": "test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "message": "这是一条测试事件",
                    "webhook_id": webhook_id,
                },
            }

            signature = self.sign_payload(test_payload, webhook.secret)
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Signature": signature,
                "X-Webhook-Event": "test",
                "X-Webhook-Timestamp": str(int(time.time())),
            }

            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(webhook.url, json=test_payload, headers=headers)
                    log = WebhookLog(
                        webhook_id=webhook_id,
                        event_type="test",
                        payload=test_payload,
                        response_code=resp.status_code,
                        attempts=1,
                        status="success" if 200 <= resp.status_code < 300 else "failed",
                    )
                    db.add(log)
                    await db.commit()
                    return {
                        "success": 200 <= resp.status_code < 300,
                        "status_code": resp.status_code,
                        "message": "测试事件已发送",
                    }
            except Exception as e:
                log = WebhookLog(
                    webhook_id=webhook_id,
                    event_type="test",
                    payload=test_payload,
                    response_code=None,
                    attempts=1,
                    status="failed",
                )
                db.add(log)
                await db.commit()
                return {"success": False, "message": f"投递失败: {str(e)}"}


# 全局单例
webhook_service = WebhookService()
