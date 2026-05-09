"""统一推送服务 - 支持飞书/钉钉/邮件/Server酱多渠道推送"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.push_channel import PushChannel, PushLog

logger = logging.getLogger(__name__)


class PushService:
    """统一推送服务，根据风险等级选择渠道推送"""

    async def send_push(
        self,
        event_id: Optional[int],
        event_type: str,
        room_name: str,
        camera_name: str,
        risk_level: int,
        event_time: datetime,
        summary: str,
        db: Optional[AsyncSession] = None,
    ) -> List[Dict]:
        """根据风险等级向所有匹配渠道推送消息，返回推送结果列表"""
        async with async_session() as _db:
            session = db if db is not None else _db
            query = select(PushChannel).where(
                PushChannel.enabled == 1,
                PushChannel.min_risk_level <= risk_level,
            )
            result = await session.execute(query)
            channels = result.scalars().all()

            if not channels:
                logger.debug("无匹配的推送渠道，跳过推送")
                return []

            content = self._build_content(
                event_type, room_name, camera_name, risk_level, event_time, summary
            )
            results = []

            for channel in channels:
                success, response_text = await self._send_to_channel(channel, content)
                log = PushLog(
                    channel_id=channel.id,
                    event_id=event_id,
                    status="success" if success else "failed",
                    response=response_text[:2000] if response_text else None,
                )
                session.add(log)
                results.append({
                    "channel_id": channel.id,
                    "channel_type": channel.channel_type,
                    "channel_name": channel.name,
                    "success": success,
                    "response": response_text,
                })

            await session.commit()
            return results

    async def send_test(self, channel: PushChannel) -> Tuple[bool, str]:
        """发送测试消息到指定渠道"""
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = (
            "\U0001f514 推送测试消息\n"
            + "渠道: " + channel.name + " (" + channel.channel_type + ")\n"
            + "时间: " + now_str + "\n"
            + "如果您收到此消息，说明推送配置正确。"
        )
        return await self._send_to_channel(channel, content)

    async def _send_to_channel(self, channel: PushChannel, content: str) -> Tuple[bool, str]:
        """根据渠道类型分发推送"""
        channel_type = channel.channel_type
        config = channel.config or {}

        try:
            if channel_type == "feishu":
                return await self._send_feishu(config, content)
            elif channel_type == "dingtalk":
                return await self._send_dingtalk(config, content)
            elif channel_type == "email":
                return await self._send_email(config, content)
            elif channel_type == "serverchan":
                return await self._send_serverchan(config, content)
            else:
                return False, "不支持的渠道类型: " + channel_type
        except Exception as e:
            logger.error("推送到 %s(%s) 失败: %s", channel.name, channel_type, e)
            return False, str(e)

    async def _send_feishu(self, config: Dict, content: str) -> Tuple[bool, str]:
        """飞书 webhook 推送"""
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return False, "飞书 webhook_url 未配置"

        payload = {"msg_type": "text", "content": {"text": content}}
        return await self._http_post(webhook_url, payload)

    async def _send_dingtalk(self, config: Dict, content: str) -> Tuple[bool, str]:
        """钉钉 webhook 推送"""
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            return False, "钉钉 webhook_url 未配置"

        payload = {"msgtype": "text", "text": {"content": content}}
        return await self._http_post(webhook_url, payload)

    async def _send_email(self, config: Dict, content: str) -> Tuple[bool, str]:
        """邮件 SMTP 推送"""
        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
        except ImportError:
            return False, "aiosmtplib 未安装"

        smtp_host = config.get("smtp_host", "")
        smtp_port = config.get("smtp_port", 587)
        username = config.get("username", "")
        password = config.get("password", "")
        sender = config.get("sender", username)
        recipients = config.get("recipients", [])
        use_tls = config.get("use_tls", True)

        if not smtp_host or not username or not recipients:
            return False, "邮件配置不完整(需要 smtp_host, username, recipients)"

        msg = MIMEMultipart()
        msg["From"] = sender
        if isinstance(recipients, list):
            msg["To"] = ", ".join(recipients)
        else:
            msg["To"] = recipients
        msg["Subject"] = "博物馆安防报警通知"
        msg.attach(MIMEText(content, "plain", "utf-8"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=int(smtp_port),
                username=username,
                password=password,
                use_tls=use_tls,
            )
            return True, "邮件发送成功"
        except Exception as e:
            return False, "邮件发送失败: " + str(e)

    async def _send_serverchan(self, config: Dict, content: str) -> Tuple[bool, str]:
        """Server酱(微信推送)"""
        key = config.get("key", "")
        if not key:
            return False, "Server酱 key 未配置"

        url = "https://sctapi.ftqq.com/" + key + ".send"
        data = {"title": "博物馆安防报警", "desp": content}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, data=data)
                resp.raise_for_status()
                return True, resp.text[:500]
        except Exception as e:
            return False, str(e)

    async def _http_post(self, url: str, payload: Dict) -> Tuple[bool, str]:
        """通用 HTTP POST 请求，带重试"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                return True, resp.text[:500]
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return False, str(e)
        return False, "未知错误"

    @staticmethod
    def _build_content(
        event_type: str,
        room_name: str,
        camera_name: str,
        risk_level: int,
        event_time: datetime,
        summary: str,
    ) -> str:
        risk_labels = {0: "正常", 1: "低风险", 2: "中风险", 3: "高风险"}
        risk_text = risk_labels.get(risk_level, "未知(" + str(risk_level) + ")")
        time_str = event_time.strftime("%Y-%m-%d %H:%M:%S")

        return (
            "\U0001f6a8 博物馆安防报警\n"
            + "事件类型: " + event_type + "\n"
            + "库房: " + room_name + "\n"
            + "摄像头: " + camera_name + "\n"
            + "风险等级: " + risk_text + "\n"
            + "时间: " + time_str + "\n"
            + "AI结论: " + summary[:500]
        )


# 全局单例
push_service = PushService()
