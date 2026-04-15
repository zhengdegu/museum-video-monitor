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

    # vLLM
    VLLM_TEXT_URL: str = "http://localhost:8000/v1"
    VLLM_VISION_URL: str = "http://localhost:8001/v1"
    VLLM_TEXT_MODEL: str = "Qwen3-32B"
    VLLM_VISION_MODEL: str = "Qwen3.5-35B-A3B"

    # Embedding
    EMBEDDING_MODEL: str = "bge-large-zh-v1.5"
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
