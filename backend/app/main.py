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
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:80", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(cameras.router, prefix="/api")
app.include_router(videos.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(inventory.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
