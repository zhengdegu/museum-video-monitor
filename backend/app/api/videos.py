import asyncio
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.video import SourceVideo
from app.models.camera import Camera
from app.models.rule import Rule
from app.schemas.event import VideoOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user
from app.services.video_analyzer import video_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["视频管理"])


@router.get("")
async def list_videos(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    camera_id: int = Query(None),
    analysis_status: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(SourceVideo)
    if camera_id:
        query = query.where(SourceVideo.camera_id == camera_id)
    if analysis_status is not None:
        query = query.where(SourceVideo.analysis_status == analysis_status)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(SourceVideo.id.desc())
    result = await db.execute(query)
    items = [VideoOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/{video_id}")
async def get_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return fail("视频不存在", 404)
    return ok(data=VideoOut.model_validate(video))


@router.delete("/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return fail("视频不存在", 404)
    await db.delete(video)
    return ok(message="删除成功")


async def _run_analysis(video_id: int, local_path: str, camera_id: int, room_id: int, rules: list):
    """后台异步执行视频分析，完成后更新状态"""
    from app.database import async_session
    try:
        await video_analyzer.analyze(video_id, local_path, camera_id, room_id, rules)
        async with async_session() as db:
            result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
            video = result.scalar_one_or_none()
            if video:
                video.analysis_status = 2
                await db.commit()
        logger.info(f"视频分析完成: video_id={video_id}")
    except Exception as e:
        logger.error(f"视频分析异常: video_id={video_id}, error={e}")
        try:
            async with async_session() as db:
                result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
                video = result.scalar_one_or_none()
                if video:
                    video.analysis_status = 3
                    await db.commit()
        except Exception:
            logger.error(f"更新分析状态失败: video_id={video_id}")


@router.post("/{video_id}/analyze")
async def trigger_analyze(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """手动触发视频分析"""
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return fail("视频不存在", 404)
    if video.analysis_status == 1:
        return fail("视频正在分析中")
    if not video.local_path:
        return fail("视频本地路径为空，无法分析")

    # 查询摄像头关联的库房ID
    cam_result = await db.execute(select(Camera).where(Camera.id == video.camera_id))
    camera = cam_result.scalar_one_or_none()
    room_id = camera.room_id if camera else 0

    # 查询启用的规则列表
    rules_result = await db.execute(select(Rule).where(Rule.enabled == 1))
    rules = [
        {"code": r.code, "name": r.name, "description": r.description,
         "rule_type": r.rule_type, "rule_config": r.rule_config, "enabled": r.enabled}
        for r in rules_result.scalars().all()
    ]

    video.analysis_status = 1
    await db.commit()

    # 启动后台异步分析任务
    asyncio.create_task(_run_analysis(video_id, video.local_path, video.camera_id, room_id, rules))

    return ok(message="已提交分析任务")
