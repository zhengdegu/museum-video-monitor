import asyncio
import json
import logging
import os
import shutil
import uuid

import aiofiles
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.video import SourceVideo
from app.models.segment import PersonSegment, VideoSegment
from app.schemas.event import VideoOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user
from app.services.video_analyzer import video_analyzer
from app.services.task_service import task_service
from app.config import settings

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
    if camera_id is not None:
        query = query.where(SourceVideo.camera_id == camera_id)
    if analysis_status is not None:
        query = query.where(SourceVideo.analysis_status == analysis_status)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(SourceVideo.id.desc())
    result = await db.execute(query)
    items = [VideoOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


# ── 分片上传 ──────────────────────────────────────────────

class UploadInitRequest(BaseModel):
    camera_id: int
    filename: str
    file_size: int
    total_chunks: int


@router.post("/upload/init")
async def upload_init(
    body: UploadInitRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    upload_id = str(uuid.uuid4())
    tmp_dir = os.path.join(settings.LOCAL_VIDEO_PATH, "tmp", upload_id)
    os.makedirs(tmp_dir, exist_ok=True)

    meta_path = os.path.join(tmp_dir, "_meta")
    async with aiofiles.open(meta_path, "w") as f:
        await f.write(json.dumps({
            "camera_id": body.camera_id,
            "filename": body.filename,
            "file_size": body.file_size,
            "total_chunks": body.total_chunks,
        }))

    video = SourceVideo(
        camera_id=body.camera_id,
        source_type=2,
        file_size=body.file_size,
        analysis_status=0,
        upload_status=1,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)

    async with aiofiles.open(meta_path, "w") as f:
        await f.write(json.dumps({
            "camera_id": body.camera_id,
            "filename": body.filename,
            "file_size": body.file_size,
            "total_chunks": body.total_chunks,
            "video_id": video.id,
        }))

    return ok(data={"upload_id": upload_id, "video_id": video.id})


@router.post("/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    _=Depends(get_current_user),
):
    tmp_dir = os.path.join(settings.LOCAL_VIDEO_PATH, "tmp", upload_id)
    # 路径遍历校验
    real_tmp = os.path.realpath(tmp_dir)
    real_base = os.path.realpath(os.path.join(settings.LOCAL_VIDEO_PATH, "tmp"))
    if not real_tmp.startswith(real_base + os.sep) and real_tmp != real_base:
        return fail("非法路径", 400)
    if not os.path.isdir(tmp_dir):
        return fail("upload_id 不存在", 400)

    chunk_path = os.path.join(tmp_dir, f"chunk_{chunk_index:06d}")
    async with aiofiles.open(chunk_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    return ok(message="分片上传成功")


@router.post("/upload/complete")
async def upload_complete(
    upload_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    tmp_dir = os.path.join(settings.LOCAL_VIDEO_PATH, "tmp", upload_id)
    # 路径遍历校验
    real_tmp = os.path.realpath(tmp_dir)
    real_base = os.path.realpath(os.path.join(settings.LOCAL_VIDEO_PATH, "tmp"))
    if not real_tmp.startswith(real_base + os.sep) and real_tmp != real_base:
        return fail("非法路径", 400)
    meta_path = os.path.join(tmp_dir, "_meta")
    if not os.path.isfile(meta_path):
        return fail("upload_id 不存在", 400)

    async with aiofiles.open(meta_path, "r") as f:
        meta = json.loads(await f.read())

    total_chunks = meta["total_chunks"]
    video_id = meta["video_id"]
    filename = meta["filename"]

    for i in range(total_chunks):
        if not os.path.isfile(os.path.join(tmp_dir, f"chunk_{i:06d}")):
            return fail(f"分片 {i} 缺失", 400)

    dest_dir = settings.LOCAL_VIDEO_PATH
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, f"{upload_id}_{filename}")

    async with aiofiles.open(dest_path, "wb") as out:
        for i in range(total_chunks):
            chunk_path = os.path.join(tmp_dir, f"chunk_{i:06d}")
            async with aiofiles.open(chunk_path, "rb") as chunk_f:
                while data := await chunk_f.read(1024 * 1024):
                    await out.write(data)

    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if video:
        video.local_path = dest_path
        video.upload_status = 2
        await db.commit()

    shutil.rmtree(tmp_dir, ignore_errors=True)

    return ok(data={"video_id": video_id, "local_path": dest_path})


@router.get("/{video_id}")
async def get_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return fail("视频不存在", 404)
    return ok(data=VideoOut.model_validate(video))


@router.get("/{video_id}/stream")
async def stream_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video or not video.local_path:
        return fail("视频文件不存在", 404)
    if not os.path.isfile(video.local_path):
        return fail("视频文件不存在于磁盘", 404)
    return FileResponse(video.local_path, media_type="video/mp4")


@router.delete("/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        return fail("视频不存在", 404)
    await db.delete(video)
    await db.commit()
    return ok(message="删除成功")


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

    video.analysis_status = 1
    await db.commit()

    task_id = await task_service.create_task(video_id, video.camera_id)
    asyncio.create_task(task_service._execute_task(task_id, video_id, video.camera_id))

    return ok(message="已提交分析任务")


@router.get("/{video_id}/segments")
async def get_video_segments(video_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """获取视频的分析片段详情（人物片段 + 动作片段）"""
    # 人物片段
    ps_result = await db.execute(
        select(PersonSegment)
        .where(PersonSegment.source_video_id == video_id)
        .order_by(PersonSegment.start_time)
    )
    person_segments = ps_result.scalars().all()

    data = []
    for ps in person_segments:
        vs_result = await db.execute(
            select(VideoSegment)
            .where(VideoSegment.person_segment_id == ps.id)
            .order_by(VideoSegment.segment_index)
        )
        video_segs = vs_result.scalars().all()

        data.append({
            "id": ps.id,
            "start_time": ps.start_time,
            "end_time": ps.end_time,
            "person_count": ps.person_count,
            "segments": [
                {
                    "id": vs.id,
                    "segment_index": vs.segment_index,
                    "start_time": vs.start_time,
                    "end_time": vs.end_time,
                    "frame_count": vs.frame_count,
                    "analysis_result": vs.analysis_result,
                    "merged_summary": vs.merged_summary,
                }
                for vs in video_segs
            ],
        })

    return ok(data=data)
