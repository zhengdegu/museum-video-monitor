"""规则引擎服务"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class RuleEngine:
    """自定义规则匹配引擎"""

    def match_rules(self, analysis_result: Dict, rules: List[Dict]) -> List[Dict]:
        """将分析结果与规则列表匹配，返回命中的规则"""
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
        config = rule.get("rule_config", {}) or {}
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
        """检查人数是否 < min_count"""
        min_count = config.get("min_count", 2)
        person_count = result.get("person_count", 0)
        if person_count > 0 and person_count < min_count:
            return {
                "rule_code": rule["code"],
                "rule_name": rule["name"],
                "hit": True,
                "confidence": 0.9,
                "detail": f"检测到 {person_count} 人进出库房，低于最低要求 {min_count} 人",
            }
        return None

    def _check_dress(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查着装是否不符合要求"""
        dress_info = result.get("dress_analysis", "")
        violations = []
        if config.get("require_uniform") and "非工作服" in str(dress_info):
            violations.append("未穿统一工作服")
        if config.get("forbid_backpack") and "背包" in str(dress_info):
            violations.append("携带背包")
        if violations:
            return {
                "rule_code": rule["code"],
                "rule_name": rule["name"],
                "hit": True,
                "confidence": 0.8,
                "detail": "着装违规: " + ", ".join(violations),
            }
        return None

    def _check_behavior(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查是否有奔跑/跳跃/躲藏"""
        violations = []
        if config.get("forbid_running") and result.get("running_detected"):
            violations.append("检测到奔跑行为")
        if config.get("forbid_jumping") and result.get("jumping_detected"):
            violations.append("检测到跳跃行为")
        if config.get("forbid_hiding") and result.get("hiding_detected"):
            violations.append("检测到躲藏行为")
        if violations:
            return {
                "rule_code": rule["code"],
                "rule_name": rule["name"],
                "hit": True,
                "confidence": 0.85,
                "detail": "行为违规: " + ", ".join(violations),
            }
        return None

    def _check_posture(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """检查手持文物姿态"""
        posture_info = result.get("posture_analysis", "")
        violations = []
        if config.get("require_dual_hand") and "单手" in str(posture_info):
            violations.append("单手持有文物")
        if config.get("require_supervisor") and result.get("person_count", 0) < 2:
            violations.append("无人在旁监督")
        if violations:
            return {
                "rule_code": rule["code"],
                "rule_name": rule["name"],
                "hit": True,
                "confidence": 0.75,
                "detail": "姿态违规: " + ", ".join(violations),
            }
        return None

    def _check_filter(self, result: Dict, rule: Dict, config: Dict) -> Optional[Dict]:
        """仅保留有人画面（此规则不产生命中，用于过滤逻辑）"""
        return None


# 全局单例
rule_engine = RuleEngine()
