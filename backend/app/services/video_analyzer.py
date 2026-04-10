"""视频分析调度器 — 完整分析管线"""
import asyncio
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

import cv2

from app.config import settings
from app.services.yolo_detector import yolo_detector
from app.services.pose_tracker import pose_tracker
from app.services.llm_analyzer import llm_analyzer
from app.services.rule_engine import rule_engine
from app.services.milvus_service import milvus_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """视频分析全流程调度"""

    async def analyze(self, video_id: int, local_path: str, camera_id: int, room_id: int, rules: List[Dict]):
        """分析一个视频的完整流程"""
        logger.info(f"[视频分析] 开始: video_id={video_id}, path={local_path}")

        try:
            # Step1: YOLO 跳帧粗扫
            logger.info(f"[Step1] YOLO 跳帧粗扫...")
            coarse_intervals = yolo_detector.detect_persons_coarse(local_path)
            if not coarse_intervals:
                logger.info(f"[Step1] 未检测到人物，跳过分析")
                return {"events": [], "status": "no_person"}

            # Step2: 扩帧精扫
            logger.info(f"[Step2] 扩帧精扫, 粗扫区间数={len(coarse_intervals)}")
            fine_intervals = yolo_detector.detect_persons_fine(local_path, coarse_intervals)

            # Step3: 短窗口合并
            logger.info(f"[Step3] 短窗口合并...")
            merged_intervals = yolo_detector.merge_intervals(fine_intervals)
            logger.info(f"[Step3] 合并后人物片段数={len(merged_intervals)}")

            all_events = []

            for seg_idx, (seg_start, seg_end) in enumerate(merged_intervals):
                logger.info(f"[分析片段 {seg_idx+1}/{len(merged_intervals)}] {seg_start:.1f}s - {seg_end:.1f}s")

                # Step4: 60s 切分 + 1秒1帧抽图
                sub_segments = self._split_segment(seg_start, seg_end)
                merged_conclusion = ""
                person_count = 0

                for sub_idx, (sub_start, sub_end) in enumerate(sub_segments):
                    # 抽帧
                    frame_dir = os.path.join(settings.LOCAL_FRAME_PATH, str(video_id), f"seg{seg_idx}_sub{sub_idx}")
                    frame_paths = self._extract_frames(local_path, sub_start, sub_end, frame_dir)

                    if not frame_paths:
                        continue

                    # YOLO 检测每帧人数
                    person_counts = []
                    yolo_boxes = []
                    for fp in frame_paths[::5]:  # 每5帧检测一次节省时间
                        frame = cv2.imread(fp)
                        if frame is not None:
                            det = yolo_detector.detect_frame(frame)
                            person_counts.append(det["person_count"])
                            yolo_boxes.extend(det["boxes"])

                    person_count = yolo_detector.get_person_count_biased(person_counts)
                    yolo_results = {"person_count": person_count, "boxes": yolo_boxes[:10]}

                    # 姿态分析（取中间帧）
                    pose_results = {"postures": [], "running_detected": False}
                    mid_frame_path = frame_paths[len(frame_paths) // 2]
                    mid_frame = cv2.imread(mid_frame_path)
                    if mid_frame is not None:
                        postures = pose_tracker.analyze_posture(mid_frame)
                        pose_results["postures"] = postures

                    # 奔跑检测
                    running = pose_tracker.detect_running(local_path, sub_start, sub_end)
                    pose_results["running_detected"] = running

                    # Step5: Qwen3.5 多模态分析
                    logger.info(f"  [Step5] 大模型分析 sub{sub_idx}: {len(frame_paths)} 帧")
                    conclusion = await llm_analyzer.analyze_segment(frame_paths, yolo_results, pose_results)

                    # Step6: 增量合并结论
                    merged_conclusion = await llm_analyzer.merge_conclusions(conclusion, merged_conclusion)

                # Step7: 裁判模型 + 规则匹配
                logger.info(f"  [Step7] 裁判判定...")
                judge_result = await llm_analyzer.judge(merged_conclusion, rules)

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
                all_events.append(event)

                # Step8: 向量化写入 Milvus
                try:
                    from app.services.rag_service import rag_service
                    embedding = await rag_service._embed(merged_conclusion)
                    event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    milvus_service.insert(
                        event_id=video_id * 1000 + seg_idx,
                        room_id=room_id,
                        camera_id=camera_id,
                        event_time=event_time,
                        description=merged_conclusion[:4000],
                        embedding=embedding,
                    )
                    logger.info(f"  [Step8] 已写入 Milvus")
                except Exception as e:
                    logger.error(f"  [Step8] Milvus 写入失败: {e}")

            # 异步推送视频到线上存储
            asyncio.create_task(storage_service.async_push_video(video_id, local_path))

            logger.info(f"[视频分析] 完成: video_id={video_id}, 事件数={len(all_events)}")
            return {"events": all_events, "status": "completed"}

        except Exception as e:
            logger.error(f"[视频分析] 失败: video_id={video_id}, error={e}")
            return {"events": [], "status": "error", "error": str(e)}

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
        interval = settings.FRAME_INTERVAL  # 1秒
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
