"""报警推送服务 — 支持飞书/钉钉 webhook（向后兼容）+ 统一推送服务"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """通过 webhook 推送报警消息到飞书或钉钉，同时调用统一推送服务"""

    async def send_alert(
        self,
        event_type: str,
        room_name: str,
        camera_name: str,
        risk_level: int,
        event_time: datetime,
        summary: str,
        event_id: Optional[int] = None,
    ) -> bool:
        # 优先使用统一推送服务
        try:
            from app.services.push_service import push_service
            results = await push_service.send_push(
                event_id=event_id,
                event_type=event_type,
                room_name=room_name,
                camera_name=camera_name,
                risk_level=risk_level,
                event_time=event_time,
                summary=summary,
            )
            if results:
                logger.info("统一推送完成，共 %d 个渠道", len(results))
                return any(r["success"] for r in results)
        except Exception as e:
            logger.warning("统一推送服务调用失败，回退到 webhook: %s", e)

        # 回退：使用环境变量中的 ALERT_WEBHOOK_URL
        url = settings.ALERT_WEBHOOK_URL
        if not url:
            logger.debug("未配置 ALERT_WEBHOOK_URL，跳过报警推送")
            return False

        risk_labels = {0: "正常", 1: "低风险", 2: "中风险", 3: "高风险"}
        risk_text = risk_labels.get(risk_level, "未知(" + str(risk_level) + ")")
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")

        content = (
            "\U0001f6a8 博物馆安防报警\n"
            "事件类型: " + event_type + "\n"
            "库房: " + room_name + "\n"
            "摄像头: " + camera_name + "\n"
            "风险等级: " + risk_text + "\n"
            "时间: " + time_str + "\n"
            "AI结论: " + summary[:500]
        )

        webhook_type = settings.ALERT_WEBHOOK_TYPE
        if webhook_type == "feishu":
            payload = self._build_feishu_payload(content)
        elif webhook_type == "dingtalk":
            payload = self._build_dingtalk_payload(content)
        else:
            logger.warning("不支持的 webhook 类型: %s", webhook_type)
            return False

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                logger.info("报警推送成功: %s, risk_level=%d", webhook_type, risk_level)
                # 同时触发开放 API Webhook 投递
                await self._dispatch_open_api_webhook(
                    event_type=event_type,
                    room_name=room_name,
                    camera_name=camera_name,
                    risk_level=risk_level,
                    event_time=event_time,
                    summary=summary,
                )
                return True
            except Exception as e:
                wait = 2 ** attempt
                if attempt < max_retries - 1:
                    logger.warning("报警推送失败(第%d次), %ds后重试: %s", attempt + 1, wait, e)
                    await asyncio.sleep(wait)
                else:
                    logger.error("报警推送最终失败(已重试%d次): %s", max_retries, e)
                    # 即使飞书/钉钉推送失败，仍然触发开放 API Webhook
                    await self._dispatch_open_api_webhook(
                        event_type=event_type,
                        room_name=room_name,
                        camera_name=camera_name,
                        risk_level=risk_level,
                        event_time=event_time,
                        summary=summary,
                    )
                    return False

    async def _dispatch_open_api_webhook(
        self,
        event_type: str,
        room_name: str,
        camera_name: str,
        risk_level: int,
        event_time: datetime,
        summary: str,
    ) -> None:
        """触发开放 API Webhook 投递"""
        try:
            from app.services.webhook_service import webhook_service

            # 确定 webhook 事件类型
            if risk_level >= 3:
                wh_event_type = "high_risk"
            else:
                wh_event_type = "violation"

            payload = {
                "event_type": wh_event_type,
                "timestamp": event_time.isoformat(),
                "data": {
                    "type": event_type,
                    "room_name": room_name,
                    "camera_name": camera_name,
                    "risk_level": risk_level,
                    "event_time": event_time.isoformat(),
                    "summary": summary[:500],
                },
            }
            await webhook_service.dispatch_event(wh_event_type, payload)
        except Exception as e:
            logger.warning("开放 API Webhook 投递触发失败: %s", e)

    @staticmethod
    def _build_feishu_payload(content: str) -> Dict:
        return {
            "msg_type": "text",
            "content": {"text": content},
        }

    @staticmethod
    def _build_dingtalk_payload(content: str) -> Dict:
        return {
            "msgtype": "text",
            "text": {"content": content},
        }


# 全局单例
alert_service = AlertService()
