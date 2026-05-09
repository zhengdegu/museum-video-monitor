"""多馆管控 - 节点管理 API"""
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.node import Node
from app.models.user import User
from app.utils.deps import get_current_user
from app.schemas.common import ok, fail
from app.services.node_service import node_service

router = APIRouter(prefix="/nodes", tags=["多馆管控"])


# ==================== Schemas ====================

class NodeCreate(BaseModel):
    name: str
    location: Optional[str] = None
    node_url: Optional[str] = None


class NodeOut(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    node_url: Optional[str] = None
    api_key: str
    status: str
    version: Optional[str] = None
    last_heartbeat_at: Optional[datetime] = None
    system_info: Optional[dict] = None
    stats: Optional[dict] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class HeartbeatData(BaseModel):
    version: Optional[str] = None
    system_info: Optional[dict] = None
    stats: Optional[dict] = None


class CommandRequest(BaseModel):
    command: str
    params: Optional[dict] = None


# ==================== 心跳接口（API Key 认证） ====================

@router.post("/heartbeat")
async def receive_heartbeat(
    body: HeartbeatData,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """接收节点心跳（通过 X-Node-Key 认证）"""
    api_key = request.headers.get("X-Node-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="缺少 X-Node-Key")

    success = await node_service.receive_heartbeat(api_key, body.model_dump(), db)
    if not success:
        raise HTTPException(status_code=401, detail="无效的节点 API Key")

    return ok(message="心跳已接收")


# ==================== 管理接口（JWT 认证） ====================

@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """全局概览"""
    data = await node_service.get_overview(db)
    return ok(data=data)


@router.get("")
async def list_nodes(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """节点列表"""
    result = await db.execute(select(Node).order_by(Node.id.desc()))
    nodes = [NodeOut.model_validate(n) for n in result.scalars().all()]
    return ok(data=nodes)


@router.get("/{node_id}")
async def get_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """节点详情"""
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    return ok(data=NodeOut.model_validate(node))


@router.post("")
async def create_node(
    body: NodeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """注册新节点（自动生成 API Key）"""
    api_key = secrets.token_urlsafe(32)
    node = Node(
        name=body.name,
        location=body.location,
        node_url=body.node_url,
        api_key=api_key,
        status="offline",
    )
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return ok(data=NodeOut.model_validate(node))


@router.delete("/{node_id}")
async def delete_node(
    node_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除节点"""
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    await db.delete(node)
    await db.flush()
    return ok(message="删除成功")


@router.post("/{node_id}/command")
async def send_command(
    node_id: int,
    body: CommandRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """向节点发送命令（预留接口）"""
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    # 预留：后续可通过 WebSocket 或 HTTP 回调向节点发送命令
    return ok(data={
        "node_id": node_id,
        "command": body.command,
        "params": body.params,
        "status": "queued",
        "message": "命令已入队（功能预留）",
    })
