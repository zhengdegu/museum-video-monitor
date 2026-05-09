"""实时预览 WebSocket 路由"""
import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.camera import Camera
from app.services.live_preview import live_preview_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/live", tags=["实时预览"])


@router.websocket("/{camera_id}")
async def live_preview_ws(websocket: WebSocket, camera_id: int):
    """WebSocket 实时预览：持续推送 YOLO 检测结果"""
    await websocket.accept()

    # 获取摄像头信息
    from app.database import async_session
    async with async_session() as db:
        camera = await db.get(Camera, camera_id)
        if not camera or not camera.rtsp_url:
            await websocket.close(code=4004, reason="摄像头不存在或无RTSP地址")
            return

    rtsp_url = camera.rtsp_url

    # 订阅实时预览
    session = await live_preview_manager.subscribe(camera_id, rtsp_url)

    try:
        while True:
            try:
                # 从队列获取检测结果，超时 5 秒发送心跳
                message = await asyncio.wait_for(session.queue.get(), timeout=5.0)
                await websocket.send_json(message)
            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket.send_json({"type": "heartbeat"})
            except WebSocketDisconnect:
                break
    except (WebSocketDisconnect, Exception) as e:
        if not isinstance(e, WebSocketDisconnect):
            logger.error(f"WebSocket 异常 camera_id={camera_id}: {e}")
    finally:
        # 连接断开时取消订阅
        await live_preview_manager.unsubscribe(camera_id)
        logger.info(f"WebSocket 断开: camera_id={camera_id}")


@router.get("/{camera_id}/snapshot")
async def get_snapshot(camera_id: int):
    """获取当前帧截图（JPEG）"""
    session = live_preview_manager.get_session(camera_id)
    if not session or not session.latest_frame:
        raise HTTPException(status_code=404, detail="无可用预览帧，请先建立WebSocket连接")

    return Response(
        content=session.latest_frame,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
