"""轨迹分析服务 — 基于 YOLO 检测框坐标的纯数学计算"""
import logging
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class TrajectoryPoint:
    """轨迹点"""
    def __init__(self, x: float, y: float, timestamp: float):
        self.x = x
        self.y = y
        self.timestamp = timestamp


class PersonTrack:
    """单个人物的轨迹"""
    def __init__(self, track_id: str):
        self.track_id = track_id
        self.points: List[TrajectoryPoint] = []
        self.first_seen: float = 0
        self.last_seen: float = 0

    def add_point(self, x: float, y: float, timestamp: float):
        point = TrajectoryPoint(x, y, timestamp)
        self.points.append(point)
        if not self.first_seen or timestamp < self.first_seen:
            self.first_seen = timestamp
        if timestamp > self.last_seen:
            self.last_seen = timestamp

    @property
    def duration(self) -> float:
        """滞留时间（秒）"""
        return self.last_seen - self.first_seen

    @property
    def total_distance(self) -> float:
        """总移动距离（像素）"""
        if len(self.points) < 2:
            return 0.0
        dist = 0.0
        for i in range(1, len(self.points)):
            dx = self.points[i].x - self.points[i - 1].x
            dy = self.points[i].y - self.points[i - 1].y
            dist += np.sqrt(dx * dx + dy * dy)
        return dist

    @property
    def average_speed(self) -> float:
        """平均速度（像素/秒）"""
        if self.duration <= 0:
            return 0.0
        return self.total_distance / self.duration

    def get_speeds(self) -> List[float]:
        """获取每段的瞬时速度"""
        speeds = []
        for i in range(1, len(self.points)):
            dx = self.points[i].x - self.points[i - 1].x
            dy = self.points[i].y - self.points[i - 1].y
            dt = self.points[i].timestamp - self.points[i - 1].timestamp
            if dt > 0:
                speed = np.sqrt(dx * dx + dy * dy) / dt
                speeds.append(speed)
        return speeds

    def get_movement_pattern(self) -> str:
        """判断移动模式：loiter（徘徊）/ linear（直线）/ back_and_forth（往返）"""
        if len(self.points) < 3:
            return "linear"

        # 计算起点到终点的直线距离
        start = self.points[0]
        end = self.points[-1]
        direct_dist = np.sqrt((end.x - start.x) ** 2 + (end.y - start.y) ** 2)

        total_dist = self.total_distance
        if total_dist <= 0:
            return "loiter"

        # 直线比率：直线距离 / 总路径距离
        linearity = direct_dist / total_dist

        # 检测往返模式：计算方向变化次数
        direction_changes = self._count_direction_changes()

        if linearity < 0.2 and self.duration > 30:
            return "loiter"
        elif direction_changes >= 3:
            return "back_and_forth"
        else:
            return "linear"

    def _count_direction_changes(self) -> int:
        """计算方向变化次数"""
        if len(self.points) < 3:
            return 0

        changes = 0
        for i in range(2, len(self.points)):
            # 前一段方向
            dx1 = self.points[i - 1].x - self.points[i - 2].x
            dy1 = self.points[i - 1].y - self.points[i - 2].y
            # 当前段方向
            dx2 = self.points[i].x - self.points[i - 1].x
            dy2 = self.points[i].y - self.points[i - 1].y

            # 用点积判断方向是否反转
            dot = dx1 * dx2 + dy1 * dy2
            mag1 = np.sqrt(dx1 * dx1 + dy1 * dy1)
            mag2 = np.sqrt(dx2 * dx2 + dy2 * dy2)

            if mag1 > 0 and mag2 > 0:
                cos_angle = dot / (mag1 * mag2)
                # 方向反转（夹角 > 120度）
                if cos_angle < -0.5:
                    changes += 1

        return changes

    def count_area_approaches(self, area_center: Tuple[float, float], radius: float) -> int:
        """计算接近某区域的次数"""
        cx, cy = area_center
        in_area = False
        approach_count = 0

        for point in self.points:
            dist = np.sqrt((point.x - cx) ** 2 + (point.y - cy) ** 2)
            if dist <= radius:
                if not in_area:
                    approach_count += 1
                    in_area = True
            else:
                in_area = False

        return approach_count

    def to_trajectory_data(self) -> Dict:
        """导出轨迹数据为 JSON 可序列化格式"""
        return {
            "track_id": self.track_id,
            "points": [{"x": p.x, "y": p.y, "t": p.timestamp} for p in self.points],
            "duration": self.duration,
            "total_distance": self.total_distance,
            "average_speed": self.average_speed,
            "movement_pattern": self.get_movement_pattern(),
        }


class TrajectoryService:
    """轨迹分析服务"""

    def __init__(self):
        # 活跃轨迹：camera_id -> {track_id -> PersonTrack}
        self._tracks: Dict[int, Dict[str, PersonTrack]] = defaultdict(dict)

    # 每个摄像头最大同时跟踪轨迹数
    MAX_TRACKS_PER_CAMERA = 50

    def update_tracks(self, camera_id: int, detections: List[Dict], timestamp: float):
        """根据 YOLO 检测结果更新轨迹

        Args:
            camera_id: 摄像头ID
            detections: YOLO 检测结果列表，每项包含 {box: [x1,y1,x2,y2], track_id: str}
            timestamp: 当前时间戳（秒）
        """
        camera_tracks = self._tracks[camera_id]

        # 先清理过期轨迹，防止内存无限增长
        self.clear_stale_tracks(camera_id)

        for det in detections:
            box = det.get("box", [])
            track_id = det.get("track_id")
            if not track_id or len(box) < 4:
                continue

            # 计算检测框中心点
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0

            if track_id not in camera_tracks:
                # 超过上限时移除最旧的轨迹
                if len(camera_tracks) >= self.MAX_TRACKS_PER_CAMERA:
                    oldest_id = min(camera_tracks, key=lambda tid: camera_tracks[tid].last_seen)
                    del camera_tracks[oldest_id]
                camera_tracks[track_id] = PersonTrack(track_id)

            camera_tracks[track_id].add_point(cx, cy, timestamp)

    def analyze_tracks(self, camera_id: int, room_id: int, rules: List[Dict]) -> List[Dict]:
        """分析指定摄像头的所有轨迹，返回触发的预警列表

        Args:
            camera_id: 摄像头ID
            room_id: 库房ID
            rules: 预警规则列表

        Returns:
            预警事件列表
        """
        warnings = []
        camera_tracks = self._tracks.get(camera_id, {})

        # 解析规则配置
        rule_configs = self._parse_rules(rules)

        for track_id, track in camera_tracks.items():
            if len(track.points) < 2:
                continue

            # 检测滞留
            loiter_warning = self._check_loiter(track, camera_id, room_id, rule_configs)
            if loiter_warning:
                warnings.append(loiter_warning)

            # 检测反复接近
            approach_warning = self._check_repeated_approach(track, camera_id, room_id, rule_configs)
            if approach_warning:
                warnings.append(approach_warning)

            # 检测突然加速
            accel_warning = self._check_acceleration(track, camera_id, room_id, rule_configs)
            if accel_warning:
                warnings.append(accel_warning)

        return warnings

    def check_off_hours(self, camera_id: int, room_id: int, current_hour: int, rules: List[Dict]) -> Optional[Dict]:
        """检测非工作时间出现人物

        Args:
            camera_id: 摄像头ID
            room_id: 库房ID
            current_hour: 当前小时（0-23）
            rules: 预警规则列表

        Returns:
            预警事件或 None
        """
        rule_configs = self._parse_rules(rules)
        off_hours_config = rule_configs.get("off_hours", {})
        if not off_hours_config.get("enabled", True):
            return None

        start_hour = off_hours_config.get("start_hour", 22)
        end_hour = off_hours_config.get("end_hour", 6)
        risk_score = off_hours_config.get("risk_score", 80)

        is_off_hours = False
        if start_hour > end_hour:
            # 跨午夜：22:00 - 06:00
            is_off_hours = current_hour >= start_hour or current_hour < end_hour
        else:
            is_off_hours = start_hour <= current_hour < end_hour

        camera_tracks = self._tracks.get(camera_id, {})
        if is_off_hours and camera_tracks:
            # 有人物轨迹存在于非工作时间
            active_tracks = [t for t in camera_tracks.values() if len(t.points) >= 2]
            if active_tracks:
                track = active_tracks[0]
                return {
                    "camera_id": camera_id,
                    "room_id": room_id,
                    "warning_type": "off_hours",
                    "risk_score": risk_score,
                    "person_track_id": track.track_id,
                    "trajectory_data": track.to_trajectory_data(),
                    "description": f"非工作时间（{start_hour}:00-{end_hour}:00）检测到人员活动",
                }

        return None

    def clear_tracks(self, camera_id: int):
        """清除指定摄像头的轨迹数据"""
        if camera_id in self._tracks:
            self._tracks[camera_id].clear()

    def clear_stale_tracks(self, camera_id: int, max_age: float = 300):
        """清除超时的轨迹（默认5分钟无更新）"""
        camera_tracks = self._tracks.get(camera_id, {})
        now = time.time()
        stale_ids = [
            tid for tid, track in camera_tracks.items()
            if now - track.last_seen > max_age
        ]
        for tid in stale_ids:
            del camera_tracks[tid]

    # ── 内部方法 ──────────────────────────────────────────

    def _parse_rules(self, rules: List[Dict]) -> Dict[str, Dict]:
        """解析规则列表为 {rule_type: config} 映射"""
        configs = {}
        for rule in rules:
            rule_type = rule.get("rule_type", "")
            config = rule.get("config", {})
            if isinstance(config, str):
                import json
                try:
                    config = json.loads(config)
                except (json.JSONDecodeError, TypeError):
                    config = {}
            configs[rule_type] = {**config, "enabled": rule.get("enabled", 1)}
        return configs

    def _check_loiter(self, track: PersonTrack, camera_id: int, room_id: int, rule_configs: Dict) -> Optional[Dict]:
        """检测滞留"""
        config = rule_configs.get("loiter", {})
        if not config.get("enabled", 1):
            return None

        threshold = config.get("threshold_seconds", 180)
        risk_score = config.get("risk_score", 60)

        if track.duration >= threshold and track.get_movement_pattern() == "loiter":
            return {
                "camera_id": camera_id,
                "room_id": room_id,
                "warning_type": "loiter",
                "risk_score": risk_score,
                "person_track_id": track.track_id,
                "trajectory_data": track.to_trajectory_data(),
                "description": f"人员在藏品区域滞留 {track.duration:.0f} 秒（阈值 {threshold} 秒），移动模式为徘徊",
            }
        return None

    def _check_repeated_approach(self, track: PersonTrack, camera_id: int, room_id: int, rule_configs: Dict) -> Optional[Dict]:
        """检测反复接近同一区域"""
        config = rule_configs.get("repeated_approach", {})
        if not config.get("enabled", 1):
            return None

        min_count = config.get("min_count", 3)
        risk_score = config.get("risk_score", 70)
        radius = config.get("radius", 50)  # 像素半径

        # 使用轨迹的重心作为关注区域
        if len(track.points) < 3:
            return None

        # 找到停留最多的区域中心
        centroid_x = np.mean([p.x for p in track.points])
        centroid_y = np.mean([p.y for p in track.points])

        approach_count = track.count_area_approaches((centroid_x, centroid_y), radius)

        if approach_count >= min_count:
            return {
                "camera_id": camera_id,
                "room_id": room_id,
                "warning_type": "repeated_approach",
                "risk_score": risk_score,
                "person_track_id": track.track_id,
                "trajectory_data": track.to_trajectory_data(),
                "description": f"人员反复接近同一区域 {approach_count} 次（阈值 {min_count} 次）",
            }
        return None

    def _check_acceleration(self, track: PersonTrack, camera_id: int, room_id: int, rule_configs: Dict) -> Optional[Dict]:
        """检测突然加速"""
        config = rule_configs.get("acceleration", {})
        if not config.get("enabled", 1):
            return None

        speed_increase_pct = config.get("speed_increase_pct", 200)  # 速度变化率阈值（百分比）
        risk_score = config.get("risk_score", 50)

        speeds = track.get_speeds()
        if len(speeds) < 3:
            return None

        # 计算速度变化率
        for i in range(1, len(speeds)):
            if speeds[i - 1] > 0:
                change_pct = ((speeds[i] - speeds[i - 1]) / speeds[i - 1]) * 100
                if change_pct >= speed_increase_pct:
                    return {
                        "camera_id": camera_id,
                        "room_id": room_id,
                        "warning_type": "acceleration",
                        "risk_score": risk_score,
                        "person_track_id": track.track_id,
                        "trajectory_data": track.to_trajectory_data(),
                        "description": f"人员突然加速，速度变化率 {change_pct:.0f}%（阈值 {speed_increase_pct}%）",
                    }
        return None


# 全局单例
trajectory_service = TrajectoryService()
