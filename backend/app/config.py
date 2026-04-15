from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "博物馆视频智能监控分析平台"
    DEBUG: bool = False
    SECRET_KEY: str  # 必须通过环境变量设置，无默认值
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:80,http://localhost"

    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str  # 必须通过环境变量设置
    MYSQL_PASSWORD: str  # 必须通过环境变量设置
    MYSQL_DATABASE: str = "museum_monitor"

    # Milvus
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "museum_events"

    # LLM API（兼容 OpenAI 协议，支持本地 vLLM / 通义千问 / DeepSeek / OpenAI 等）
    VLLM_TEXT_URL: str = "http://localhost:8000/v1"
    VLLM_VISION_URL: str = "http://localhost:8001/v1"
    VLLM_TEXT_MODEL: str = "Qwen3-32B"
    VLLM_VISION_MODEL: str = "Qwen3.5-35B-A3B"
    VLLM_API_KEY: str = "not-needed"  # 文本模型 API Key
    VLLM_VISION_API_KEY: str = ""  # 视觉模型 API Key，为空时复用 VLLM_API_KEY

    # Embedding
    EMBEDDING_URL: str = ""  # 为空时复用 VLLM_TEXT_URL
    EMBEDDING_MODEL: str = "bge-large-zh-v1.5"
    EMBEDDING_API_KEY: str = ""  # 为空时复用 VLLM_API_KEY
    RERANKER_MODEL: str = "bge-reranker-v2-m3"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str  # 必须通过环境变量设置
    MINIO_SECRET_KEY: str  # 必须通过环境变量设置
    MINIO_BUCKET: str = "museum-videos"

    # Storage
    LOCAL_VIDEO_PATH: str = "./data/videos"
    LOCAL_FRAME_PATH: str = "./data/frames"

    # YOLO
    YOLO_MODEL_PATH: str = "./models/yolo11m.pt"
    YOLO_POSE_MODEL_PATH: str = "./models/yolo11m-pose.pt"
    YOLO_CONFIDENCE: float = 0.5
    YOLO_INPUT_SIZE: int = 640

    # Alert Webhook
    ALERT_WEBHOOK_URL: str = ""
    ALERT_WEBHOOK_TYPE: str = "feishu"  # feishu / dingtalk

    # Cleanup
    VIDEO_RETENTION_HOURS: int = 24  # 已分析视频保留时长（小时）

    # RTSP
    RTSP_SEGMENT_DURATION: int = 300  # 默认5分钟切片

    # Video Analysis
    SKIP_FRAME_INTERVAL: int = 25
    PERSON_EXPAND_SECONDS: float = 5.0
    MERGE_GAP_SECONDS: float = 3.0
    SEGMENT_DURATION: int = 60
    FRAME_INTERVAL: int = 1

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
