"""YOLO-Pose + ByteTracker 姿态追踪服务"""
import logging
from typing import List, Dict, Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class PoseTracker:
    """姿态检测与行为分析"""

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            from ultralytics import YOLO
            self._model = YOLO(settings.YOLO_POSE_MODEL_PATH)
            logger.info(f"YOLO-Pose 模型已加载: {settings.YOLO_POSE_MODEL_PATH}")

    def detect_running(self, video_path: str, start_sec: float, end_sec: float, consecutive_threshold: int = 5) -> bool:
        """奔跑检测：连续帧判定，避免转身误判"""
        self._load_model()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)

        consecutive_running = 0
        prev_positions: Dict[int, np.ndarray] = {}

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        frame_idx = start_frame

        while frame_idx <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            results = self._model(frame, verbose=False)
            if results and results[0].keypoints is not None:
                keypoints = results[0].keypoints.xy.cpu().numpy()
                is_running = self._check_running_pose(keypoints, prev_positions, fps)
                if is_running:
                    consecutive_running += 1
                    if consecutive_running >= consecutive_threshold:
                        cap.release()
                        return True
                else:
                    consecutive_running = 0

                # 更新位置记录
                for i, kp in enumerate(keypoints):
                    if len(kp) > 0:
                        center = kp.mean(axis=0)
                        prev_positions[i] = center

            frame_idx += 1

        cap.release()
        return False

    def _check_running_pose(self, keypoints: np.ndarray, prev_positions: Dict[int, np.ndarray], fps: float) -> bool:
        """通过关键点位移速度判断是否奔跑"""
        speed_threshold = 150.0 / fps  # 像素/帧，可调

        for i, kp in enumerate(keypoints):
            if len(kp) == 0:
                continue
            center = kp.mean(axis=0)
            if i in prev_positions:
                displacement = np.linalg.norm(center - prev_positions[i])
                if displacement > speed_threshold:
                    return True
        return False

    def analyze_posture(self, frame: np.ndarray) -> List[Dict]:
        """姿态分析：返回每个人的关键点"""
        self._load_model()
        results = self._model(frame, verbose=False)
        persons = []

        if results and results[0].keypoints is not None:
            keypoints = results[0].keypoints.xy.cpu().numpy()
            confs = results[0].keypoints.conf.cpu().numpy() if results[0].keypoints.conf is not None else None

            for i, kp in enumerate(keypoints):
                person = {
                    "person_id": i,
                    "keypoints": kp.tolist(),
                    "confidence": confs[i].tolist() if confs is not None else [],
                }
                # COCO 关键点: 0鼻 1左眼 2右眼 ... 9左手腕 10右手腕
                if len(kp) >= 11:
                    left_wrist = kp[9]
                    right_wrist = kp[10]
                    person["left_wrist"] = left_wrist.tolist()
                    person["right_wrist"] = right_wrist.tolist()
                persons.append(person)

        return persons

    def track_persons(self, video_path: str, start_sec: float = 0, end_sec: float = None) -> List[Dict]:
        """ByteTrack 多目标追踪：返回每个人的运动轨迹"""
        self._load_model()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        start_frame = int(start_sec * fps)
        end_frame = int((end_sec or total_frames / fps) * fps)
        end_frame = min(end_frame, total_frames)

        tracks: Dict[int, List] = {}
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        for frame_idx in range(start_frame, end_frame):
            ret, frame = cap.read()
            if not ret:
                break

            results = self._model.track(frame, persist=True, verbose=False)
            if results and results[0].boxes.id is not None:
                ids = results[0].boxes.id.cpu().numpy().astype(int)
                boxes = results[0].boxes.xyxy.cpu().numpy()
                for track_id, box in zip(ids, boxes):
                    tid = int(track_id)
                    if tid not in tracks:
                        tracks[tid] = []
                    cx = (box[0] + box[2]) / 2
                    cy = (box[1] + box[3]) / 2
                    tracks[tid].append({
                        "frame": frame_idx,
                        "time": frame_idx / fps,
                        "center": [float(cx), float(cy)],
                        "bbox": box.tolist(),
                    })

        cap.release()

        return [{"track_id": tid, "positions": positions} for tid, positions in tracks.items()]


# 全局单例
pose_tracker = PoseTracker()
