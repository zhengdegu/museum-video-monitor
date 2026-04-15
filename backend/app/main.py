from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import engine, Base
from app.api import rooms, cameras, videos, events, rules, collections, chat, auth, inventory


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 启动 RTSP 拉流服务
    from app.services.video_puller import video_puller
    try:
        await video_puller.start_all_cameras()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"拉流服务启动失败: {e}")

    # 恢复未完成的分析任务
    from app.services.task_service import task_service
    try:
        await task_service.recover_stale_tasks()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"任务恢复失败: {e}")

    # 启动视频文件定期清理
    from app.services.cleanup_service import cleanup_service
    try:
        await cleanup_service.start()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"清理服务启动失败: {e}")

    yield

    # 停止清理服务
    try:
        await cleanup_service.stop()
    except Exception:
        pass

    # 停止拉流
    try:
        await video_puller.stop_all()
    except Exception:
        pass
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（/api/v1/ 前缀）
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(rooms.router, prefix=API_PREFIX)
app.include_router(cameras.router, prefix=API_PREFIX)
app.include_router(videos.router, prefix=API_PREFIX)
app.include_router(events.router, prefix=API_PREFIX)
app.include_router(rules.router, prefix=API_PREFIX)
app.include_router(collections.router, prefix=API_PREFIX)
app.include_router(chat.router, prefix=API_PREFIX)
app.include_router(inventory.router, prefix=API_PREFIX)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
