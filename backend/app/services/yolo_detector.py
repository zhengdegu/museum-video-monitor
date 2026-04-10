"""YOLO11 目标检测服务"""
import logging
import os
from typing import List, Tuple

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class YOLODetector:
    """YOLO11 人物检测 + 跳帧粗扫 + 扩帧精扫 + 短窗口合并"""

    def __init__(self):
        self.confidence = settings.YOLO_CONFIDENCE
        self.input_size = settings.YOLO_INPUT_SIZE
        self._model = None

    def _load_model(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(settings.YOLO_MODEL_PATH)
            logger.info(f"YOLO 模型已加载: {settings.YOLO_MODEL_PATH}")

    def detect_persons_coarse(self, video_path: str, skip_frames: int = None) -> List[Tuple[float, float]]:
        """跳帧粗扫：返回粗略人物时间区间列表 [(start_sec, end_sec), ...]"""
        self._load_model()
        skip_frames = skip_frames or settings.SKIP_FRAME_INTERVAL

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频: {video_path}")
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        logger.info(f"跳帧粗扫: {video_path}, fps={fps}, total={total_frames}, skip={skip_frames}")

        person_timestamps = []
        frame_idx = 0

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            results = self._model(frame, imgsz=self.input_size, conf=self.confidence, classes=[0], verbose=False)
            if results and len(results[0].boxes) > 0:
                timestamp = frame_idx / fps
                person_timestamps.append(timestamp)

            frame_idx += skip_frames
            if frame_idx >= total_frames:
                break

        cap.release()

        if not person_timestamps:
            return []

        # 将时间点转为区间（每个点 ± skip_frames/fps 的范围）
        interval = skip_frames / fps
        intervals = [(max(0, t - interval), t + interval) for t in person_timestamps]
        return self.merge_intervals(intervals)

    def detect_persons_fine(self, video_path: str, intervals: List[Tuple[float, float]], expand_sec: float = None) -> List[Tuple[float, float]]:
        """扩帧精扫：对粗扫区间前后扩展，逐帧精确检测"""
        self._load_model()
        expand_sec = expand_sec or settings.PERSON_EXPAND_SECONDS

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return intervals

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps

        refined = []
        for start, end in intervals:
            scan_start = max(0, start - expand_sec)
            scan_end = min(duration, end + expand_sec)

            first_person = None
            last_person = None

            frame_idx = int(scan_start * fps)
            end_frame = int(scan_end * fps)

            while frame_idx <= end_frame and frame_idx < total_frames:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break

                results = self._model(frame, imgsz=self.input_size, conf=self.confidence, classes=[0], verbose=False)
                if results and len(results[0].boxes) > 0:
                    t = frame_idx / fps
                    if first_person is None:
                        first_person = t
                    last_person = t

                frame_idx += 1  # 逐帧

            if first_person is not None and last_person is not None:
                refined.append((first_person, last_person))

        cap.release()
        return self.merge_intervals(refined) if refined else []

    def detect_frame(self, frame: np.ndarray) -> dict:
        """检测单帧，返回人物数量和检测框"""
        self._load_model()
        results = self._model(frame, imgsz=self.input_size, conf=self.confidence, classes=[0], verbose=False)
        boxes = []
        if results and len(results[0].boxes) > 0:
            for box in results[0].boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = float(box.conf[0])
                boxes.append({"bbox": [x1, y1, x2, y2], "confidence": conf})
        return {"person_count": len(boxes), "boxes": boxes}

    def merge_intervals(self, intervals: List[Tuple[float, float]], gap_sec: float = None) -> List[Tuple[float, float]]:
        """短窗口合并：gap < gap_sec 的区间合并"""
        gap_sec = gap_sec or settings.MERGE_GAP_SECONDS
        if not intervals:
            return []
        sorted_iv = sorted(intervals, key=lambda x: x[0])
        merged = [list(sorted_iv[0])]
        for start, end in sorted_iv[1:]:
            if start - merged[-1][1] <= gap_sec:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return [(s, e) for s, e in merged]

    def get_person_count_biased(self, counts: List[int], percentile: float = 0.8) -> int:
        """偏向值处理：取80%置信度下的最多人数"""
        if not counts:
            return 0
        sorted_counts = sorted(counts, reverse=True)
        idx = max(0, int(len(sorted_counts) * (1 - percentile)))
        return sorted_counts[idx]


# 全局单例
yolo_detector = YOLODetector()
