"""规则引擎匹配逻辑测试 — 直接测试 RuleEngine 类，不依赖数据库"""
import pytest
from app.services.rule_engine import RuleEngine

engine = RuleEngine()


def _rule(rule_type: str, config: dict, name: str = "test", code: str = "T001") -> dict:
    return {"name": name, "code": code, "rule_type": rule_type, "rule_config": config, "enabled": 1}


# ---------- person_count ----------

class TestPersonCount:
    def test_hit_below_min(self):
        result = {"person_count": 1}
        rule = _rule("person_count", {"min_count": 2})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert hits[0]["confidence"] == 0.9
        assert "1 人" in hits[0]["detail"]

    def test_no_hit_when_enough(self):
        result = {"person_count": 3}
        rule = _rule("person_count", {"min_count": 2})
        assert engine.match_rules(result, [rule]) == []

    def test_no_hit_when_zero(self):
        """person_count == 0 不触发（条件是 0 < count < min）"""
        result = {"person_count": 0}
        rule = _rule("person_count", {"min_count": 2})
        assert engine.match_rules(result, [rule]) == []


# ---------- dress ----------

class TestDress:
    def test_hit_structured_no_uniform(self):
        result = {"dress_violations": [{"type": "no_uniform"}]}
        rule = _rule("dress", {"require_uniform": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert "未穿统一工作服" in hits[0]["detail"]

    def test_hit_structured_backpack(self):
        result = {"dress_violations": [{"type": "backpack"}]}
        rule = _rule("dress", {"forbid_backpack": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert "背包" in hits[0]["detail"]

    def test_hit_text_fallback(self):
        result = {"text": "该人员穿着便装进入库房"}
        rule = _rule("dress", {"require_uniform": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1

    def test_no_hit_when_compliant(self):
        result = {"dress_violations": []}
        rule = _rule("dress", {"require_uniform": True})
        assert engine.match_rules(result, [rule]) == []


# ---------- behavior ----------

class TestBehavior:
    def test_hit_running_structured(self):
        result = {"running_detected": True}
        rule = _rule("behavior", {"forbid_running": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert "奔跑" in hits[0]["detail"]

    def test_hit_running_text_fallback(self):
        result = {"text": "有人在库房内奔跑"}
        rule = _rule("behavior", {"forbid_running": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1

    def test_no_hit_when_not_configured(self):
        result = {"running_detected": True}
        rule = _rule("behavior", {"forbid_jumping": True})  # 只禁止跳跃
        assert engine.match_rules(result, [rule]) == []


# ---------- posture ----------

class TestPosture:
    def test_hit_single_hand(self):
        result = {"posture_analysis": {"single_hand": True}}
        rule = _rule("posture", {"require_dual_hand": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert "单手" in hits[0]["detail"]

    def test_hit_no_supervisor(self):
        result = {"person_count": 1}
        rule = _rule("posture", {"require_supervisor": True})
        hits = engine.match_rules(result, [rule])
        assert len(hits) == 1
        assert "监督" in hits[0]["detail"]

    def test_no_hit_with_supervisor(self):
        result = {"person_count": 2}
        rule = _rule("posture", {"require_supervisor": True})
        assert engine.match_rules(result, [rule]) == []


# ---------- disabled / filter ----------

class TestMisc:
    def test_disabled_rule_skipped(self):
        result = {"person_count": 1}
        rule = _rule("person_count", {"min_count": 2})
        rule["enabled"] = 0
        assert engine.match_rules(result, [rule]) == []

    def test_filter_rule_no_hit(self):
        result = {"person_count": 5}
        rule = _rule("filter", {})
        assert engine.match_rules(result, [rule]) == []

    def test_string_input_wrapped(self):
        """传入字符串时应自动包装为 {"text": ...}"""
        rule = _rule("dress", {"require_uniform": True})
        hits = engine.match_rules("该人员穿着便装", [rule])
        assert len(hits) == 1

    def test_multiple_rules(self):
        result = {"person_count": 1, "running_detected": True}
        rules = [
            _rule("person_count", {"min_count": 2}, code="R01"),
            _rule("behavior", {"forbid_running": True}, code="R02"),
        ]
        hits = engine.match_rules(result, rules)
        assert len(hits) == 2
        codes = {h["rule_code"] for h in hits}
        assert codes == {"R01", "R02"}
