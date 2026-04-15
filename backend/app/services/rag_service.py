"""RAG 检索服务"""
import asyncio
import logging
from typing import AsyncGenerator, Dict, Optional, List

import numpy as np
from openai import AsyncOpenAI

from app.config import settings
from app.services.milvus_service import milvus_service

logger = logging.getLogger(__name__)


class RAGService:
    """基于 Milvus + bge + Qwen3 的 RAG 检索链路"""

    def __init__(self):
        embed_url = settings.EMBEDDING_URL or settings.VLLM_TEXT_URL
        embed_key = settings.EMBEDDING_API_KEY or settings.VLLM_API_KEY
        self.embed_client = AsyncOpenAI(base_url=embed_url, api_key=embed_key)
        self.llm_client = AsyncOpenAI(base_url=settings.VLLM_TEXT_URL, api_key=settings.VLLM_API_KEY)
        self.text_model = settings.VLLM_TEXT_MODEL
        self.embed_model = settings.EMBEDDING_MODEL

    async def query(self, message: str, session_id: Optional[str] = None) -> Dict:
        """完整 RAG 流程"""
        try:
            # 1. 向量化 query
            query_embedding = await self._embed(message)

            # 2. Milvus Top-K 召回
            hits = await asyncio.to_thread(milvus_service.search, query_embedding, 20)
            if not hits:
                return {
                    "answer": "未找到相关事件记录。请确认查询条件或等待更多视频分析完成。",
                    "sources": [],
                    "session_id": session_id,
                }

            # 3. Rerank
            descriptions = [h["description"] for h in hits]
            reranked_indices = await self._rerank(query_embedding, descriptions)
            top_hits = [hits[i] for i in reranked_indices[:5]]

            # 4. LLM 组织回答
            context = "\n\n".join([
                f"[事件{i+1}] 库房ID:{h['room_id']} | 摄像头ID:{h['camera_id']} | 时间:{h['event_time']}\n{h['description']}"
                for i, h in enumerate(top_hits)
            ])

            prompt = f"""你是博物馆视频安防智能助手。请根据以下检索到的事件记录回答用户问题。

检索到的事件记录：
{context}

用户问题：{message}

回答要求：
1. 简洁准确，引用具体时间和库房信息
2. 如有违规事件，重点标注
3. 如果检索结果无法回答问题，如实说明"""

            response = await self.llm_client.chat.completions.create(
                model=self.text_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
            )

            answer = response.choices[0].message.content
            sources = [
                {"event_id": h["event_id"], "room_id": h["room_id"], "camera_id": h["camera_id"],
                 "event_time": h["event_time"], "score": h["score"]}
                for h in top_hits
            ]

            return {"answer": answer, "sources": sources, "session_id": session_id}

        except Exception as e:
            logger.error(f"RAG 查询失败: {e}")
            return {
                "answer": f"查询出错: {str(e)}。请确保 Milvus 和 vLLM 服务已启动。",
                "sources": [],
                "session_id": session_id,
            }

    async def query_stream(self, message: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """流式 RAG 流程，逐 token yield SSE data"""
        try:
            query_embedding = await self._embed(message)
            hits = await asyncio.to_thread(milvus_service.search, query_embedding, 20)
            if not hits:
                yield "data: 未找到相关事件记录。请确认查询条件或等待更多视频分析完成。\n\n"
                yield "data: [DONE]\n\n"
                return

            descriptions = [h["description"] for h in hits]
            reranked_indices = await self._rerank(query_embedding, descriptions)
            top_hits = [hits[i] for i in reranked_indices[:5]]

            context = "\n\n".join([
                f"[事件{i+1}] 库房ID:{h['room_id']} | 摄像头ID:{h['camera_id']} | 时间:{h['event_time']}\n{h['description']}"
                for i, h in enumerate(top_hits)
            ])

            prompt = f"""你是博物馆视频安防智能助手。请根据以下检索到的事件记录回答用户问题。

检索到的事件记录：
{context}

用户问题：{message}

回答要求：
1. 简洁准确，引用具体时间和库房信息
2. 如有违规事件，重点标注
3. 如果检索结果无法回答问题，如实说明"""

            stream = await self.llm_client.chat.completions.create(
                model=self.text_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.1,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield f"data: {delta}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"RAG 流式查询失败: {e}")
            yield f"data: 查询出错: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    async def _embed(self, text: str) -> List[float]:
        """文本向量化 (bge-large-zh-v1.5)"""
        try:
            response = await self.embed_client.embeddings.create(
                model=self.embed_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding 失败: {e}")
            return [0.0] * 1024

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量文本向量化（单次 API 调用）"""
        try:
            response = await self.embed_client.embeddings.create(
                model=self.embed_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"批量 Embedding 失败: {e}")
            return [[0.0] * 1024 for _ in texts]

    async def _rerank(self, query_embedding: List[float], documents: List[str]) -> List[int]:
        """重排序：批量 embed 后计算相似度排序"""
        try:
            query_vec = np.array(query_embedding)
            # 批量 embed 所有文档（单次 API 调用替代逐个调用）
            doc_embeddings = await self._embed_batch(documents)
            doc_matrix = np.array(doc_embeddings)
            # 向量化计算余弦相似度
            norms = np.linalg.norm(doc_matrix, axis=1)
            query_norm = np.linalg.norm(query_vec)
            scores = np.dot(doc_matrix, query_vec) / (norms * query_norm + 1e-8)

            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            return ranked

        except Exception as e:
            logger.error(f"Rerank 失败: {e}")
            return list(range(len(documents)))


# 全局单例
rag_service = RAGService()
