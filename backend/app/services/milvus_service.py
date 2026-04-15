"""Milvus 向量存储服务 — 支持 Milvus Lite（URI模式）和 Milvus Server（host:port模式）"""
import logging
import time
from typing import List, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# 延迟导入 pymilvus，避免 CI 上 marshmallow 依赖冲突
_pymilvus = None


def _get_pymilvus():
    global _pymilvus
    if _pymilvus is None:
        import pymilvus
        _pymilvus = pymilvus
    return _pymilvus


class MilvusService:
    """Milvus 向量库操作：事件向量化存储与检索"""

    COLLECTION_NAME = "museum_events"
    DIM = 1024

    def __init__(self):
        self._connected = False
        self._collection = None
        self._loaded = False
        self._use_lite = bool(settings.MILVUS_URI)

    def connect(self):
        if self._connected:
            return
        pm = _get_pymilvus()
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                if self._use_lite:
                    pm.connections.connect(alias="default", uri=settings.MILVUS_URI)
                    logger.info(f"Milvus Lite 已连接: {settings.MILVUS_URI}")
                else:
                    pm.connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
                    logger.info(f"Milvus Server 已连接: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
                self._connected = True
                return
            except Exception as e:
                logger.warning(f"Milvus 连接失败 (第{attempt}/{max_retries}次): {e}")
                if attempt < max_retries:
                    time.sleep(5)
                else:
                    logger.error("Milvus 连接重试耗尽，放弃连接")
                    raise

    def create_collection(self):
        self.connect()
        pm = _get_pymilvus()
        if pm.utility.has_collection(self.COLLECTION_NAME):
            self._collection = pm.Collection(self.COLLECTION_NAME)
            logger.info(f"Collection 已存在: {self.COLLECTION_NAME}")
            return

        fields = [
            pm.FieldSchema(name="id", dtype=pm.DataType.INT64, is_primary=True, auto_id=True),
            pm.FieldSchema(name="event_id", dtype=pm.DataType.INT64),
            pm.FieldSchema(name="room_id", dtype=pm.DataType.INT64),
            pm.FieldSchema(name="camera_id", dtype=pm.DataType.INT64),
            pm.FieldSchema(name="event_time", dtype=pm.DataType.VARCHAR, max_length=64),
            pm.FieldSchema(name="description", dtype=pm.DataType.VARCHAR, max_length=4096),
            pm.FieldSchema(name="embedding", dtype=pm.DataType.FLOAT_VECTOR, dim=self.DIM),
        ]
        schema = pm.CollectionSchema(fields=fields, description="博物馆安防事件向量库")
        self._collection = pm.Collection(name=self.COLLECTION_NAME, schema=schema)

        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        self._collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Collection 已创建: {self.COLLECTION_NAME}")

    def _get_collection(self):
        if self._collection is None:
            self.create_collection()
        return self._collection

    def insert(self, event_id: int, room_id: int, camera_id: int, event_time: str, description: str, embedding: List[float]):
        coll = self._get_collection()
        if len(description) > 4096:
            description = description[:4096]
        data = [[event_id], [room_id], [camera_id], [event_time], [description], [embedding]]
        coll.insert(data)
        coll.flush()
        logger.info(f"写入 Milvus: event_id={event_id}")

    def search(self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        coll = self._get_collection()
        if not self._loaded:
            coll.load()
            self._loaded = True

        search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
        expr = None
        if filters:
            conditions = []
            if "room_id" in filters:
                conditions.append(f"room_id == {filters['room_id']}")
            if "camera_id" in filters:
                conditions.append(f"camera_id == {filters['camera_id']}")
            if conditions:
                expr = " and ".join(conditions)

        results = coll.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["event_id", "room_id", "camera_id", "event_time", "description"],
        )

        hits = []
        for hit in results[0]:
            hits.append({
                "event_id": hit.entity.get("event_id"),
                "room_id": hit.entity.get("room_id"),
                "camera_id": hit.entity.get("camera_id"),
                "event_time": hit.entity.get("event_time"),
                "description": hit.entity.get("description"),
                "score": hit.score,
            })
        return hits


# 全局单例
milvus_service = MilvusService()
