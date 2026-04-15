"""规则引擎服务 — 结构化 JSON 匹配"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RuleEngine:
    """基于结构化 JSON config 的规则匹配引擎"""

    def match_rules(self, analysis_result, rules: List[Dict]) -> List[Dict]:
        """将分析结果与规则列表匹配，返回命中的规则"""
        if isinstance(analysis_result, str):
            analysis_result = {"text": analysis_result}
        hits = []
        for rule in rules:
            if not rule.get("enabled", 1):
                continue
            hit = self._check_rule(analysis_result, rule)
            if hit:
                hits.append(hit)
        return hits

    def _check_rule(self, result: Dict, rule: Dict) -> Optional[Dict]:
        rule_type = rule.get("rule_type", "")
        config = rule.get("rule_config") or {}
        if isinstance(config, str):
            import json
            try:
                config = json.loads(config)
            except (json.JSONDecodeError, TypeError):
                config = {}

        checkers = {
            "person_count": self._check_person_count,
            "dress": self._check_dress,
            "behavior": self._check_behavior,
            "posture": self._check_posture,
            "filter": self._check_filter,
        }
        checker = checkers.get(rule_type)
        if checker:
            return checker(result, rule, config)
        return None

    def _check_person_count(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查人数是否 < min_count — 基于结构化字段"""
        min_count = config.get("min_count", 2)
        person_count = result.get("person_count", 0)
        if isinstance(person_count, (int, float)) and 0 < person_count < min_count:
            return self._hit(rule, 0.9, f"检测到 {person_count} 人进出库房，低于最低要求 {min_count} 人")
        return None

    def _check_dress(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查着装 — 优先使用结构化字段 dress_violations，回退到文本"""
        violations = []
        dress_violations = result.get("dress_violations", [])
        if isinstance(dress_violations, list) and dress_violations:
            if config.get("require_uniform") and any(v.get("type") == "no_uniform" for v in dress_violations):
                violations.append("未穿统一工作服")
            if config.get("forbid_backpack") and any(v.get("type") == "backpack" for v in dress_violations):
                violations.append("携带背包")
        else:
            # 回退：从文本中匹配关键词
            text = result.get("text", "") + str(result.get("dress_analysis", ""))
            if config.get("require_uniform") and any(kw in text for kw in ("非工作服", "便装", "未穿")):
                violations.append("未穿统一工作服")
            if config.get("forbid_backpack") and any(kw in text for kw in ("背包", "书包", "挎包")):
                violations.append("携带背包")
        if violations:
            return self._hit(rule, 0.8, "着装违规: " + ", ".join(violations))
        return None

    def _check_behavior(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查危险行为 — 优先使用结构化布尔字段"""
        violations = []
        checks = [
            ("forbid_running", "running_detected", ("奔跑", "跑步"), "检测到奔跑行为"),
            ("forbid_jumping", "jumping_detected", ("跳跃", "跳"), "检测到跳跃行为"),
            ("forbid_hiding", "hiding_detected", ("躲藏", "躲避"), "检测到躲藏行为"),
        ]
        text = result.get("text", "")
        for config_key, field_key, keywords, msg in checks:
            if not config.get(config_key):
                continue
            # 优先结构化字段
            if result.get(field_key):
                violations.append(msg)
            elif any(kw in text for kw in keywords):
                violations.append(msg)
        if violations:
            return self._hit(rule, 0.85, "行为违规: " + ", ".join(violations))
        return None

    def _check_posture(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查手持文物姿态 — 优先使用结构化字段"""
        violations = []
        posture_data = result.get("posture_analysis") or {}
        text = result.get("text", "") + str(result.get("posture_analysis", ""))

        if config.get("require_dual_hand"):
            if isinstance(posture_data, dict) and posture_data.get("single_hand"):
                violations.append("单手持有文物")
            elif any(kw in text for kw in ("单手", "一只手")):
                violations.append("单手持有文物")

        if config.get("require_supervisor"):
            person_count = result.get("person_count", 0)
            if isinstance(person_count, (int, float)) and person_count < 2:
                violations.append("无人在旁监督")

        if violations:
            return self._hit(rule, 0.75, "姿态违规: " + ", ".join(violations))
        return None

    def _check_filter(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """仅保留有人画面（此规则不产生命中）"""
        return None

    @staticmethod
    def _hit(rule: Dict, confidence: float, detail: str) -> Dict:
        return {
            "rule_code": rule["code"],
            "rule_name": rule["name"],
            "hit": True,
            "confidence": confidence,
            "detail": detail,
        }


# 全局单例
rule_engine = RuleEngine()
