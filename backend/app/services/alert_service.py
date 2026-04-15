"""报警推送服务 — 支持飞书/钉钉 webhook"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """通过 webhook 推送报警消息到飞书或钉钉"""

    async def send_alert(
        self,
        event_type: str,
        room_name: str,
        camera_name: str,
        risk_level: int,
        event_time: datetime,
        summary: str,
    ) -> bool:
        url = settings.ALERT_WEBHOOK_URL
        if not url:
            logger.debug("未配置 ALERT_WEBHOOK_URL，跳过报警推送")
            return False

        risk_labels = {0: "正常", 1: "低风险", 2: "中风险", 3: "高风险"}
        risk_text = risk_labels.get(risk_level, f"未知({risk_level})")
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")

        content = (
            f"🚨 博物馆安防报警\n"
            f"事件类型: {event_type}\n"
            f"库房: {room_name}\n"
            f"摄像头: {camera_name}\n"
            f"风险等级: {risk_text}\n"
            f"时间: {time_str}\n"
            f"AI结论: {summary[:500]}"
        )

        webhook_type = settings.ALERT_WEBHOOK_TYPE
        if webhook_type == "feishu":
            payload = self._build_feishu_payload(content)
        elif webhook_type == "dingtalk":
            payload = self._build_dingtalk_payload(content)
        else:
            logger.warning(f"不支持的 webhook 类型: {webhook_type}")
            return False

        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                logger.info(f"报警推送成功: {webhook_type}, risk_level={risk_level}")
                return True
            except Exception as e:
                wait = 2 ** attempt  # 1s, 2s, 4s
                if attempt < max_retries - 1:
                    logger.warning(f"报警推送失败(第{attempt+1}次), {wait}s后重试: {e}")
                    await asyncio.sleep(wait)
                else:
                    logger.error(f"报警推送最终失败(已重试{max_retries}次): {e}")
                    return False

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
