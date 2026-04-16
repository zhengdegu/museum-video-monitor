"""Agent 巡检 API — 供 OpenClaw 或外部调用"""
from fastapi import APIRouter, Depends, Query
from app.schemas.common import ok
from app.utils.deps import get_current_user
from app.services.agent_service import agent_service

router = APIRouter(prefix="/agent", tags=["Agent 自动化"])


@router.get("/patrol")
async def patrol(_=Depends(get_current_user)):
    """触发巡检，返回结构化报告"""
    report = await agent_service.generate_patrol_report()
    return ok(data={"report": report})


@router.get("/alerts")
async def alerts(
    hours: int = Query(1, ge=1, le=72, description="检查最近N小时的报警"),
    _=Depends(get_current_user),
):
    """检查最近的违规报警事件"""
    messages = await agent_service.generate_alert_messages(hours=hours)
    return ok(data={"count": len(messages), "alerts": messages})


@router.get("/daily-report")
async def daily_report(_=Depends(get_current_user)):
    """生成当日安防日报"""
    report = await agent_service.generate_daily_report()
    return ok(data={"report": report})


@router.get("/health")
async def health_summary(_=Depends(get_current_user)):
    """系统健康状态汇总"""
    summary = await agent_service.health_summary()
    return ok(data=summary)
