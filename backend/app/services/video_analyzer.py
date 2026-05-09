"""视频分析调度器 — 完整分析管线（已拆分为独立步骤函数）"""
import asyncio
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

import cv2

from app.config import settings
from app.services.yolo_detector import yolo_detector
from app.services.pose_tracker import pose_tracker
from app.services.llm_analyzer import llm_analyzer
from app.services.rule_engine import rule_engine
from app.services.vector_service import vector_service
from app.services.storage_service import storage_service
from app.services.alert_service import alert_service
from app.services.trajectory_service import trajectory_service

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """视频分析全流程调度"""

    async def analyze(self, video_id: int, local_path: str, camera_id: int, room_id: int, rules: List[Dict], task_id: Optional[int] = None):
        """分析一个视频的完整流程

        注意：任务状态由 task_service 统一管理，本方法不再操作任务状态。
        """
        logger.info(f"[视频分析] 开始: video_id={video_id}, path={local_path}")

        # 记录本次分析产生的帧图目录，用于最终清理
        frame_dirs: List[str] = []

        try:
            # Step1-3: 人物检测与区间合并
            merged_intervals = await self._step_detect_persons(local_path)
            if not merged_intervals:
                return {"events": [], "status": "no_person"}

            all_events = []
            for seg_idx, (seg_start, seg_end) in enumerate(merged_intervals):
                logger.info(f"[分析片段 {seg_idx+1}/{len(merged_intervals)}] {seg_start:.1f}s - {seg_end:.1f}s")

                event = await self._step_analyze_segment(
                    video_id, local_path, camera_id, room_id, rules,
                    seg_idx, seg_start, seg_end, frame_dirs,
                )
                if event:
                    all_events.append(event)

            # 创建聚合事件记录
            if all_events:
                await self._step_create_aggregate(video_id, camera_id, room_id, all_events)

            # 异步推送视频到线上存储
            try:
                push_task = asyncio.create_task(storage_service.async_push_video(video_id, local_path))

                def _on_push_done(t: asyncio.Task):
                    if t.exception():
                        logger.error(f"[视频推送] 异步推送失败: video_id={video_id}, error={t.exception()}")

                push_task.add_done_callback(_on_push_done)
            except Exception as e:
                logger.error(f"[视频推送] 创建推送任务失败: video_id={video_id}, error={e}")

            logger.info(f"[视频分析] 完成: video_id={video_id}, 事件数={len(all_events)}")
            return {"events": all_events, "status": "completed"}

        except Exception as e:
            logger.error(f"[视频分析] 失败: video_id={video_id}, error={e}")
            return {"events": [], "status": "error", "error": str(e)}

        finally:
            # 清理本次分析产生的所有帧图目录
            self._cleanup_frame_dirs(video_id, frame_dirs)

    # ── Step 1-3: 人物检测 ──────────────────────────────────

    async def _step_detect_persons(self, local_path: str) -> List[Tuple[float, float]]:
        """YOLO 粗扫 → 精扫 → 合并，返回人物出现的时间区间列表"""
        logger.info("[Step1] YOLO 跳帧粗扫...")
        coarse_intervals = await asyncio.to_thread(yolo_detector.detect_persons_coarse, local_path)
        if not coarse_intervals:
            logger.info("[Step1] 未检测到人物，跳过分析")
            return []

        logger.info(f"[Step2] 扩帧精扫, 粗扫区间数={len(coarse_intervals)}")
        fine_intervals = await asyncio.to_thread(yolo_detector.detect_persons_fine, local_path, coarse_intervals)

        logger.info("[Step3] 短窗口合并...")
        merged = await asyncio.to_thread(yolo_detector.merge_intervals, fine_intervals)
        logger.info(f"[Step3] 合并后人物片段数={len(merged)}")
        return merged

    # ── Step 4-8: 单片段分析 ────────────────────────────────

    async def _step_analyze_segment(
        self, video_id: int, local_path: str, camera_id: int, room_id: int,
        rules: List[Dict], seg_idx: int, seg_start: float, seg_end: float,
        frame_dirs: List[str],
    ) -> Optional[Dict]:
        """分析单个人物片段：切分子段 → 逐段分析 → 裁判判定 → 写库 → 向量化"""
        from app.database import async_session
        from app.models.segment import PersonSegment, VideoSegment
        from app.models.event import Event, EventAggregate
        from app.models.rule import RuleHit

        sub_segments = self._split_segment(seg_start, seg_end)
        merged_conclusion = ""
        person_count = 0

        # 创建 person_segment 记录
        person_segment_id = None
        async with async_session() as db:
            ps = PersonSegment(source_video_id=video_id, start_time=seg_start, end_time=seg_end, person_count=0)
            db.add(ps)
            await db.commit()
            await db.refresh(ps)
            person_segment_id = ps.id

        # Step4-6: 逐子段分析
        for sub_idx, (sub_start, sub_end) in enumerate(sub_segments):
            result = await self._step_analyze_sub_segment(
                video_id, local_path, seg_idx, sub_idx, sub_start, sub_end, person_segment_id, frame_dirs, camera_id,
            )
            if result:
                person_count = result["person_count"]
                merged_conclusion = result["merged_conclusion"]

        # 更新 person_segment 的人数
        async with async_session() as db:
            from sqlalchemy import select as sa_select
            from app.models.segment import PersonSegment as PS
            result = await db.execute(sa_select(PS).where(PS.id == person_segment_id))
            ps_record = result.scalar_one_or_none()
            if ps_record:
                ps_record.person_count = person_count
                await db.commit()

        # Step7: 裁判判定 + 本地规则匹配
        judge_result = await self._step_judge(merged_conclusion, rules)

        # 构造事件
        event = {
            "video_id": video_id,
            "camera_id": camera_id,
            "room_id": room_id,
            "segment_start": seg_start,
            "segment_end": seg_end,
            "person_count": person_count,
            "conclusion": merged_conclusion,
            "judge_result": judge_result,
            "risk_level": judge_result.get("risk_level", 0),
            "rule_hits": [h for h in judge_result.get("rule_hits", []) if h.get("hit")],
        }

        # 写入 event + rule_hit 记录
        await self._step_persist_event(event, video_id, person_segment_id, camera_id, room_id, person_count, merged_conclusion, judge_result)

        # 轨迹预警检查
        try:
            current_hour = datetime.now().hour
            await self._step_trajectory_check(camera_id, room_id, current_hour)
        except Exception as e:
            logger.error(f"[轨迹预警] 检查失败: {e}")

        # Step8: 向量化写入 Milvus
        await self._step_vectorize(room_id, camera_id, merged_conclusion)

        return event

    async def _step_analyze_sub_segment(
        self, video_id: int, local_path: str, seg_idx: int, sub_idx: int,
        sub_start: float, sub_end: float, person_segment_id: int,
        frame_dirs: List[str], camera_id: int = 0,
    ) -> Optional[Dict]:
        """分析单个 60s 子段：抽帧 → YOLO → 姿态 → LLM → 合并结论"""
        from app.database import async_session
        from app.models.segment import VideoSegment

        frame_dir = os.path.join(settings.LOCAL_FRAME_PATH, str(video_id), f"seg{seg_idx}_sub{sub_idx}")
        frame_dirs.append(frame_dir)  # 记录帧图目录，供后续清理
        frame_paths = await asyncio.to_thread(self._extract_frames, local_path, sub_start, sub_end, frame_dir)
        if not frame_paths:
            return None

        # YOLO 检测
        person_counts, yolo_boxes = await asyncio.to_thread(self._detect_frames_sync, frame_paths)
        person_count = await asyncio.to_thread(yolo_detector.get_person_count_biased, person_counts)
        yolo_results = {"person_count": person_count, "boxes": yolo_boxes[:10]}

        # 轨迹分析：将 YOLO 检测框送入轨迹服务
        await self._step_trajectory_update(camera_id, yolo_boxes, sub_start, sub_end)

        # 姿态分析
        pose_results = await self._step_pose_analysis(frame_paths, local_path, sub_start, sub_end)

        # Step5: LLM 多模态分析
        logger.info(f"  [Step5] 大模型分析 sub{sub_idx}: {len(frame_paths)} 帧")
        conclusion = await llm_analyzer.analyze_segment(frame_paths, yolo_results, pose_results)

        # Step6: 增量合并结论
        merged_conclusion = await llm_analyzer.merge_conclusions(conclusion, "")

        # 写入 video_segment 记录
        async with async_session() as db:
            vs = VideoSegment(
                person_segment_id=person_segment_id,
                segment_index=sub_idx,
                start_time=sub_start,
                end_time=sub_end,
                frame_count=len(frame_paths),
                analysis_result={"conclusion": conclusion},
                merged_summary=merged_conclusion[:4000] if merged_conclusion else None,
            )
            db.add(vs)
            await db.commit()

        return {"person_count": person_count, "merged_conclusion": merged_conclusion}

    async def _step_pose_analysis(
        self, frame_paths: List[str], local_path: str, sub_start: float, sub_end: float,
    ) -> Dict:
        """姿态分析：取中间帧分析姿态 + 奔跑检测"""
        pose_results: Dict = {"postures": [], "running_detected": False}
        mid_frame_path = frame_paths[len(frame_paths) // 2]
        mid_frame = await asyncio.to_thread(cv2.imread, mid_frame_path)
        if mid_frame is not None:
            postures = await asyncio.to_thread(pose_tracker.analyze_posture, mid_frame)
            pose_results["postures"] = postures
        running = await asyncio.to_thread(pose_tracker.detect_running, local_path, sub_start, sub_end)
        pose_results["running_detected"] = running
        return pose_results

    # ── 轨迹分析 ──────────────────────────────────────────

    async def _step_trajectory_update(self, camera_id: int, yolo_boxes: List[Dict], sub_start: float, sub_end: float):
        """将 YOLO 检测框更新到轨迹服务（纯内存操作）"""
        # 将 boxes 转换为带 track_id 的检测列表
        # yolo_boxes 格式: [{"box": [x1,y1,x2,y2], "track_id": "...", ...}]
        mid_time = (sub_start + sub_end) / 2.0
        detections = []
        for i, box_data in enumerate(yolo_boxes):
            if isinstance(box_data, dict):
                detections.append(box_data)
            elif isinstance(box_data, (list, tuple)) and len(box_data) >= 4:
                detections.append({"box": box_data, "track_id": f"person_{i}"})
        if detections:
            trajectory_service.update_tracks(camera_id, detections, mid_time)

    async def _step_trajectory_check(
        self, camera_id: int, room_id: int, current_hour: int,
    ) -> List[Dict]:
        """执行轨迹预警检查并写入数据库"""
        from app.database import async_session
        from app.models.warning import Warning as WarningModel, WarningRule
        from sqlalchemy import select as sa_select

        # 加载预警规则
        async with async_session() as db:
            result = await db.execute(sa_select(WarningRule).where(WarningRule.enabled == 1))
            rules = result.scalars().all()
            rule_dicts = [{"rule_type": r.rule_type, "config": r.config, "enabled": r.enabled} for r in rules]

        # 分析轨迹
        warnings = trajectory_service.analyze_tracks(camera_id, room_id, rule_dicts)

        # 检查非工作时间
        off_hours_warning = trajectory_service.check_off_hours(camera_id, room_id, current_hour, rule_dicts)
        if off_hours_warning:
            warnings.append(off_hours_warning)

        # 写入数据库
        if warnings:
            async with async_session() as db:
                for w in warnings:
                    db_warning = WarningModel(
                        camera_id=w["camera_id"],
                        room_id=w["room_id"],
                        warning_type=w["warning_type"],
                        risk_score=w["risk_score"],
                        person_track_id=w.get("person_track_id"),
                        trajectory_data=w.get("trajectory_data"),
                        description=w.get("description", ""),
                        status="active",
                    )
                    db.add(db_warning)
                await db.commit()
            logger.info(f"[轨迹预警] camera_id={camera_id}, 新增 {len(warnings)} 条预警")

        # 清理过期轨迹
        trajectory_service.clear_stale_tracks(camera_id)

        return warnings

    # ── Step 7: 裁判判定 ───────────────────────────────────

    async def _step_judge(self, merged_conclusion: str, rules: List[Dict]) -> Dict:
        """LLM 裁判判定 + 本地规则引擎匹配，合并结果"""
        logger.info("  [Step7] 裁判判定...")
        judge_result = await llm_analyzer.judge(merged_conclusion, rules)
        local_hits = await asyncio.to_thread(rule_engine.match_rules, merged_conclusion, rules)
        existing_hits = judge_result.get("rule_hits", [])
        judge_result["rule_hits"] = existing_hits + [h for h in local_hits if h not in existing_hits]
        return judge_result

    # ── 持久化 ─────────────────────────────────────────────

    async def _step_persist_event(
        self, event: Dict, video_id: int, person_segment_id: int,
        camera_id: int, room_id: int, person_count: int,
        merged_conclusion: str, judge_result: Dict,
    ):
        """写入 event 和 rule_hit 记录到数据库"""
        from app.database import async_session
        from app.models.event import Event
        from app.models.rule import RuleHit
        from sqlalchemy import select as sa_sel
        from app.models.rule import Rule as RuleModel

        async with async_session() as db:
            db_event = Event(
                source_video_id=video_id,
                person_segment_id=person_segment_id,
                camera_id=camera_id,
                room_id=room_id,
                event_time=datetime.now(),
                event_type="violation" if event["rule_hits"] else "normal",
                person_count=person_count,
                description=judge_result.get("summary", ""),
                ai_conclusion=merged_conclusion[:4000] if merged_conclusion else None,
            )
            db.add(db_event)
            await db.commit()
            await db.refresh(db_event)

            for hit in event["rule_hits"]:
                rule_code = hit.get("rule_code", "")
                actual_rule_id = None
                if rule_code:
                    r_result = await db.execute(sa_sel(RuleModel.id).where(RuleModel.code == rule_code))
                    row = r_result.scalar_one_or_none()
                    if row:
                        actual_rule_id = row
                if actual_rule_id is None:
                    logger.warning(f"rule_code={rule_code} 未找到对应规则，跳过写入 rule_hit")
                    continue
                rule_hit = RuleHit(
                    event_id=db_event.id,
                    rule_id=actual_rule_id,
                    hit_time=datetime.now(),
                    confidence=hit.get("confidence", 0),
                    detail=hit.get("detail", ""),
                )
                db.add(rule_hit)
            await db.commit()
            event["event_db_id"] = db_event.id

        # 报警推送：risk_level >= 2 时触发
        risk_level = judge_result.get("risk_level", 0)
        if risk_level >= 2:
            try:
                from app.models.camera import Camera
                from app.models.room import StorageRoom
                async with async_session() as db:
                    cam = await db.get(Camera, camera_id)
                    room = await db.get(StorageRoom, room_id)
                    camera_name = cam.name if cam else f"摄像头{camera_id}"
                    room_name = room.name if room else f"库房{room_id}"
                await alert_service.send_alert(
                    event_type=event.get("judge_result", {}).get("summary", "violation"),
                    room_name=room_name,
                    camera_name=camera_name,
                    risk_level=risk_level,
                    event_time=datetime.now(),
                    summary=merged_conclusion[:500] if merged_conclusion else "",
                )
            except Exception as e:
                logger.error(f"报警推送异常: {e}")

    async def _step_create_aggregate(
        self, video_id: int, camera_id: int, room_id: int, all_events: List[Dict],
    ):
        """创建聚合事件记录"""
        from app.database import async_session
        from app.models.event import EventAggregate

        first_start = min(e["segment_start"] for e in all_events)
        last_end = max(e["segment_end"] for e in all_events)
        base_time = datetime.now()
        actual_start = base_time - timedelta(seconds=(last_end - first_start))
        actual_end = base_time

        async with async_session() as db:
            agg = EventAggregate(
                room_id=room_id,
                camera_id=camera_id,
                session_start=actual_start,
                session_end=actual_end,
                total_events=len(all_events),
                rule_hits=sum(len(e.get("rule_hits", [])) for e in all_events),
                summary=f"视频 {video_id} 分析完成，共 {len(all_events)} 个事件",
                risk_level=max(e.get("risk_level", 0) for e in all_events),
            )
            db.add(agg)
            await db.commit()

    # ── Step 8: 向量化 ────────────────────────────────────

    async def _step_vectorize(self, room_id: int, camera_id: int, merged_conclusion: str):
        """向量化写入 Milvus"""
        try:
            from app.services.rag_service import rag_service
            embedding = await rag_service._embed(merged_conclusion)
            event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            event_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
            await asyncio.to_thread(
                vector_service.insert,
                event_id=event_id,
                room_id=room_id,
                camera_id=camera_id,
                event_time=event_time,
                description=merged_conclusion[:4000],
                embedding=embedding,
            )
            logger.info("  [Step8] 已写入 Milvus")
        except Exception as e:
            logger.error(f"  [Step8] Milvus 写入失败: {e}")


    # ── 帧图清理 ──────────────────────────────────────────

    def _cleanup_frame_dirs(self, video_id: int, frame_dirs: List[str]):
        """清理分析过程中产生的帧图目录"""
        for d in frame_dirs:
            try:
                if os.path.isdir(d):
                    shutil.rmtree(d)
            except Exception as e:
                logger.warning(f"清理帧图目录失败: {d}, error={e}")

        # 尝试清理 video_id 级别的父目录（如果为空）
        video_frame_dir = os.path.join(settings.LOCAL_FRAME_PATH, str(video_id))
        try:
            if os.path.isdir(video_frame_dir) and not os.listdir(video_frame_dir):
                os.rmdir(video_frame_dir)
        except Exception:
            pass

        if frame_dirs:
            logger.info(f"[帧图清理] video_id={video_id}, 已清理 {len(frame_dirs)} 个帧图目录")

    # ── 工具方法 ───────────────────────────────────────────

    @staticmethod
    def _detect_frames_sync(frame_paths: List[str]):
        """同步检测帧列表中的人物（供 asyncio.to_thread 调用）"""
        person_counts = []
        yolo_boxes = []
        for fp in frame_paths[::5]:
            frame = cv2.imread(fp)
            if frame is not None:
                det = yolo_detector.detect_frame(frame)
                person_counts.append(det["person_count"])
                yolo_boxes.extend(det["boxes"])
        return person_counts, yolo_boxes

    def _split_segment(self, start: float, end: float, duration: int = None) -> List[tuple]:
        """将人物大片段按 60s 切分"""
        duration = duration or settings.SEGMENT_DURATION
        segments = []
        t = start
        while t < end:
            seg_end = min(t + duration, end)
            segments.append((t, seg_end))
            t = seg_end
        return segments

    def _extract_frames(self, video_path: str, start_sec: float, end_sec: float, output_dir: str) -> List[str]:
        """从视频中抽帧：1秒1帧"""
        os.makedirs(output_dir, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        interval = settings.FRAME_INTERVAL
        frame_paths = []
        current_sec = start_sec
        while current_sec <= end_sec:
            frame_idx = int(current_sec * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            filename = f"frame_{current_sec:.1f}.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            frame_paths.append(filepath)
            current_sec += interval
        cap.release()
        logger.info(f"抽帧完成: {len(frame_paths)} 帧, {start_sec:.1f}s-{end_sec:.1f}s")
        return frame_paths


# 全局单例
video_analyzer = VideoAnalyzer()
