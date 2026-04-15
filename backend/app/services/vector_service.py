"""ChromaDB 向量存储服务"""
import logging
from typing import List, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class VectorService:
    """ChromaDB 向量库操作：事件向量化存储与检索"""

    def __init__(self):
        self._client = None
        self._collection = None

    def _ensure_client(self):
        if self._client is not None:
            return
        import chromadb
        self._client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"ChromaDB 已初始化: {settings.CHROMA_PERSIST_DIR}, collection={settings.CHROMA_COLLECTION}")

    def insert(self, event_id: int, room_id: int, camera_id: int, event_time: str, description: str, embedding: List[float]):
        self._ensure_client()
        if len(description) > 4096:
            description = description[:4096]
        self._collection.add(
            ids=[str(event_id)],
            embeddings=[embedding],
            documents=[description],
            metadatas=[{
                "event_id": event_id,
                "room_id": room_id,
                "camera_id": camera_id,
                "event_time": event_time,
            }],
        )
        logger.info(f"写入 ChromaDB: event_id={event_id}")

    def search(self, query_embedding: List[float], top_k: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        self._ensure_client()
        where = None
        if filters:
            conditions = []
            if "room_id" in filters:
                conditions.append({"room_id": filters["room_id"]})
            if "camera_id" in filters:
                conditions.append({"camera_id": filters["camera_id"]})
            if len(conditions) == 1:
                where = conditions[0]
            elif len(conditions) > 1:
                where = {"$and": conditions}

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )

        hits = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i]
                distance = results["distances"][0][i] if results.get("distances") else 0.0
                score = 1.0 - distance  # cosine distance -> similarity
                hits.append({
                    "event_id": meta.get("event_id"),
                    "room_id": meta.get("room_id"),
                    "camera_id": meta.get("camera_id"),
                    "event_time": meta.get("event_time"),
                    "description": results["documents"][0][i],
                    "score": score,
                })
        return hits


# 全局单例
vector_service = VectorService()
