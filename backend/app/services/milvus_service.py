"""Milvus 向量存储服务"""
import logging
from typing import List, Dict, Optional

from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

from app.config import settings

logger = logging.getLogger(__name__)


class MilvusService:
    """Milvus 向量库操作：事件向量化存储与检索"""

    COLLECTION_NAME = "museum_events"
    DIM = 1024

    def __init__(self):
        self._connected = False
        self._collection: Optional[Collection] = None
        self._loaded = False

    def connect(self):
        if not self._connected:
            connections.connect(host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
            self._connected = True
            logger.info(f"Milvus 已连接: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")

    def create_collection(self):
        self.connect()
        if utility.has_collection(self.COLLECTION_NAME):
            self._collection = Collection(self.COLLECTION_NAME)
            logger.info(f"Collection 已存在: {self.COLLECTION_NAME}")
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="event_id", dtype=DataType.INT64),
            FieldSchema(name="room_id", dtype=DataType.INT64),
            FieldSchema(name="camera_id", dtype=DataType.INT64),
            FieldSchema(name="event_time", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.DIM),
        ]
        schema = CollectionSchema(fields=fields, description="博物馆安防事件向量库")
        self._collection = Collection(name=self.COLLECTION_NAME, schema=schema)

        # 创建索引
        index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
        self._collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Collection 已创建: {self.COLLECTION_NAME}")

    def _get_collection(self) -> Collection:
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
