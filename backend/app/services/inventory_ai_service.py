"""AI 自动盘点服务"""
import asyncio
import base64
import json
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Optional

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.camera import Camera
from app.models.collection import Collection
from app.models.inventory_task import AiInventoryTask, AiInventoryResult, AiInventorySchedule

logger = logging.getLogger(__name__)


class InventoryAiService:
    """AI 自动盘点服务"""

    async def trigger_inventory(self, room_id: int, trigger_type: str = "manual") -> int:
        """触发一次 AI 盘点任务"""
        async with async_session() as db:
            task = AiInventoryTask(
                room_id=room_id,
                trigger_type=trigger_type,
                status="pending",
            )
            db.add(task)
            await db.commit()
            await db.refresh(task)
            task_id = task.id
        asyncio.create_task(self._execute_inventory(task_id, room_id))
        return task_id

    async def _execute_inventory(self, task_id: int, room_id: int):
        """执行盘点流程"""
        async with async_session() as db:
            task = await db.get(AiInventoryTask, task_id)
            if not task:
                return
            task.status = "running"
            task.started_at = datetime.now()
            await db.commit()

        try:
            async with async_session() as db:
                result = await db.execute(
                    select(Camera).where(Camera.room_id == room_id, Camera.status == 1)
                )
                cameras = result.scalars().all()

            if not cameras:
                await self._fail_task(task_id, "no online cameras")
                return

            async with async_session() as db:
                result = await db.execute(
                    select(Collection).where(Collection.room_id == room_id)
                )
                collections = result.scalars().all()

            if not collections:
                await self._fail_task(task_id, "no collections in room")
                return

            frame_paths: List[str] = []
            for cam in cameras:
                fp = await self._capture_frame(cam)
                if fp:
                    frame_paths.append(fp)

            if not frame_paths:
                await self._fail_task(task_id, "all cameras capture failed")
                return

            collection_list = [
                {"id": c.id, "name": c.name, "code": c.code, "description": c.description or ""}
                for c in collections
            ]
            ai_results = await self._analyze_with_vision(frame_paths, collection_list)
            await self._save_results(task_id, ai_results, frame_paths, len(collections))

        except Exception as e:
            logger.error(f"AI inventory task {task_id} failed: {e}")
            await self._fail_task(task_id, str(e))

    async def _capture_frame(self, camera: Camera) -> Optional[str]:
        """Use ffmpeg to capture one frame from RTSP stream"""
        save_dir = os.path.join(settings.LOCAL_FRAME_PATH, "inventory")
        os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inv_cam{camera.id}_{timestamp}.jpg"
        filepath = os.path.join(save_dir, filename)

        # 通过 MediaMTX 中转地址抓帧，避免直连摄像头冲突
        mediamtx_url = f"{settings.MEDIAMTX_RTSP_URL}/cam{camera.id}"
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", mediamtx_url,
            "-frames:v", "1",
            "-q:v", "2",
            filepath,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                err_msg = stderr.decode(errors="replace")[-300:] if stderr else "unknown"
                logger.error(f"Capture failed camera_id={camera.id}: {err_msg}")
                return None

            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                logger.info(f"Captured: {filepath}")
                return filepath
            return None

        except asyncio.TimeoutError:
            logger.error(f"Capture timeout camera_id={camera.id}")
            return None
        except Exception as e:
            logger.error(f"Capture error camera_id={camera.id}: {e}")
            return None

    async def _analyze_with_vision(self, frame_paths: List[str], collection_list: List[Dict]) -> List[Dict]:
        """Call vision LLM to analyze frames"""
        from app.services.llm_analyzer import llm_analyzer

        image_contents = []
        for fp in frame_paths:
            if os.path.exists(fp):
                with open(fp, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                })

        lines = []
        for c in collection_list:
            lines.append(f"- code: {c['code']}, name: {c['name']}, desc: {c['description']}")
        collection_text = "\n".join(lines)

        prompt = (
            "You are a museum collection inventory expert. "
            "Observe the surveillance screenshots below, identify collections, "
            "and compare with the reference list to determine each item's status.\n\n"
            "Reference list:\n" + collection_text + "\n\n"
            "For each item, determine:\n"
            "- present: clearly visible in frame\n"
            "- missing: should be there but not found\n"
            "- displaced: visible but position abnormal\n"
            "- uncertain: cannot determine\n\n"
            "Output JSON array, each element:\n"
            "- collection_id: item code value\n"
            "- status: present/missing/displaced/uncertain\n"
            "- confidence: 0.0-1.0\n"
            "- description: brief note\n\n"
            "Output only JSON array, nothing else."
        )

        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}] + image_contents}]

        try:
            response = await llm_analyzer.vision_client.chat.completions.create(
                model=llm_analyzer.vision_model,
                messages=messages,
                max_tokens=4000,
                temperature=0.1,
                timeout=120,
            )
            text = response.choices[0].message.content.strip()
            return self._parse_results(text, collection_list)
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return [
                {"collection_id": c["id"], "status": "uncertain", "confidence": 0.0, "description": str(e)}
                for c in collection_list
            ]

    def _parse_results(self, text: str, collection_list: List[Dict]) -> List[Dict]:
        """Parse LLM JSON response"""
        parsed = None

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            pass

        if not parsed:
            md_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
            if md_match:
                try:
                    parsed = json.loads(md_match.group(1))
                except json.JSONDecodeError:
                    pass

        if not parsed:
            arr_match = re.search(r"\[.*\]", text, re.DOTALL)
            if arr_match:
                try:
                    parsed = json.loads(arr_match.group(0))
                except json.JSONDecodeError:
                    pass

        if not parsed or not isinstance(parsed, list):
            logger.warning(f"AI inventory parse failed: {text[:300]}")
            return [
                {"collection_id": c["id"], "status": "uncertain", "confidence": 0.0, "description": "parse failed"}
                for c in collection_list
            ]

        code_to_id = {c["code"]: c["id"] for c in collection_list}
        id_set = {c["id"] for c in collection_list}
        results = []

        for item in parsed:
            cid = item.get("collection_id")
            if cid in code_to_id:
                actual_id = code_to_id[cid]
            elif isinstance(cid, int) and cid in id_set:
                actual_id = cid
            else:
                continue

            status = item.get("status", "uncertain")
            if status not in ("present", "missing", "displaced", "uncertain"):
                status = "uncertain"

            confidence = float(item.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))

            results.append({
                "collection_id": actual_id,
                "status": status,
                "confidence": confidence,
                "description": item.get("description", ""),
            })

        covered_ids = {r["collection_id"] for r in results}
        for c in collection_list:
            if c["id"] not in covered_ids:
                results.append({
                    "collection_id": c["id"],
                    "status": "uncertain",
                    "confidence": 0.0,
                    "description": "not mentioned by AI",
                })

        return results

    async def _save_results(self, task_id: int, ai_results: List[Dict], frame_paths: List[str], total_items: int):
        """Save inventory results to database"""
        matched = sum(1 for r in ai_results if r["status"] == "present")
        missing = sum(1 for r in ai_results if r["status"] == "missing")
        uncertain = sum(1 for r in ai_results if r["status"] in ("uncertain", "displaced"))

        frame_path_str = frame_paths[0] if frame_paths else None

        async with async_session() as db:
            for r in ai_results:
                record = AiInventoryResult(
                    task_id=task_id,
                    collection_id=r["collection_id"],
                    status=r["status"],
                    confidence=r["confidence"],
                    description=r["description"],
                    frame_path=frame_path_str,
                )
                db.add(record)

            task = await db.get(AiInventoryTask, task_id)
            if task:
                task.status = "completed"
                task.completed_at = datetime.now()
                task.total_items = total_items
                task.matched_items = matched
                task.missing_items = missing
                task.uncertain_items = uncertain

            await db.commit()

        logger.info(f"AI inventory {task_id} done: total={total_items} present={matched} missing={missing} uncertain={uncertain}")

    async def _fail_task(self, task_id: int, error_message: str):
        """Mark task as failed"""
        async with async_session() as db:
            task = await db.get(AiInventoryTask, task_id)
            if task:
                task.status = "failed"
                task.completed_at = datetime.now()
                task.error_message = error_message
                await db.commit()
        logger.error(f"AI inventory {task_id} failed: {error_message}")


# Global singleton
inventory_ai_service = InventoryAiService()
