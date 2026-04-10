from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ok
from app.utils.deps import get_current_user
from app.services.rag_service import rag_service

router = APIRouter(prefix="/chat", tags=["NLP智能交互"])


@router.get("/stream")
async def chat_stream(
    message: str = Query(...),
    session_id: str = Query(None),
    _=Depends(get_current_user),
):
    """SSE 流式自然语言查询"""
    return StreamingResponse(
        rag_service.query_stream(message, session_id=session_id),
        media_type="text/event-stream",
    )


@router.post("")
async def chat(body: ChatRequest, _=Depends(get_current_user)):
    """自然语言查询事件"""
    result = await rag_service.query(body.message, session_id=body.session_id)
    return ok(data=ChatResponse(
        answer=result.get("answer", "暂无法回答该问题"),
        sources=result.get("sources", []),
        session_id=result.get("session_id", body.session_id),
    ))
