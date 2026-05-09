"""Milvus 向量存储服务"""
import logging
from typing import List, Dict, Optional

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)

from app.config import settings

logger = logging.getLogger(__name__)

# Schema 常量
COLLECTION_NAME = settings.MILVUS_COLLECTION
EMBEDDING_DIM = 1024


class VectorService:
    """Milvus 向量库操作：事件向量化存储与检索"""

    def __init__(self):
        self._collection: Optional[Collection] = None
        self._connected = False

    def _ensure_connection(self):
        """确保已连接到 Milvus"""
        if self._connected:
            return
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        self._connected = True
        logger.info(f"Milvus 已连接: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

    def init_collection(self):
        """创建 collection（如不存在），并加载到内存"""
        self._ensure_connection()

        if utility.has_collection(COLLECTION_NAME):
            self._collection = Collection(COLLECTION_NAME)
            self._collection.load()
            logger.info(f"Milvus collection 已存在并加载: {COLLECTION_NAME}")
            return

        # 定义 Schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="room_id", dtype=DataType.INT64),
            FieldSchema(name="camera_id", dtype=DataType.INT64),
            FieldSchema(name="event_time", dtype=DataType.VARCHAR, max_length=32),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=4000),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields=fields, description="博物馆事件向量库")
        self._collection = Collection(name=COLLECTION_NAME, schema=schema)

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        self._collection.create_index(field_name="embedding", index_params=index_params)
        self._collection.load()
        logger.info(f"Milvus collection 已创建并加载: {COLLECTION_NAME}")

    def _ensure_collection(self):
        """确保 collection 已初始化"""
        if self._collection is None:
            self.init_collection()

    def insert(self, event_id: int, room_id: int, camera_id: int, event_time: str, description: str, embedding: List[float]):
        """插入单条事件向量"""
        self._ensure_collection()
        if len(description) > 4000:
            description = description[:4000]
        data = [
            [event_id],       # id
            [room_id],        # room_id
            [camera_id],      # camera_id
            [event_time],     # event_time
            [description],    # description
            [embedding],      # embedding
        ]
        self._collection.insert(data)
        self._collection.flush()
        logger.info(f"写入 Milvus: event_id={event_id}")

    def search(self, query_embedding: List[float], top_k: int = 20, filters: Optional[Dict] = None) -> List[Dict]:
        """向量检索，返回 [{event_id, room_id, camera_id, event_time, description, score}]"""
        self._ensure_collection()

        # 构建过滤表达式
        expr = None
        if filters:
            conditions = []
            if "room_id" in filters:
                conditions.append(f"room_id == {filters['room_id']}")
            if "camera_id" in filters:
                conditions.append(f"camera_id == {filters['camera_id']}")
            if conditions:
                expr = " and ".join(conditions)

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16},
        }

        results = self._collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["id", "room_id", "camera_id", "event_time", "description"],
        )

        hits = []
        if results and len(results) > 0:
            for hit in results[0]:
                hits.append({
                    "event_id": hit.entity.get("id"),
                    "room_id": hit.entity.get("room_id"),
                    "camera_id": hit.entity.get("camera_id"),
                    "event_time": hit.entity.get("event_time"),
                    "description": hit.entity.get("description"),
                    "score": hit.score,  # COSINE 相似度，越大越相似
                })
        return hits

    def delete_by_ids(self, ids: List[int]):
        """按 ID 批量删除"""
        self._ensure_collection()
        if not ids:
            return
        expr = f"id in {ids}"
        self._collection.delete(expr)
        self._collection.flush()
        logger.info(f"从 Milvus 删除: ids={ids}")


# 全局单例
vector_service = VectorService()
