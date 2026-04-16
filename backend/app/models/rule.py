from sqlalchemy import Column, Integer, String, Float, Text, DateTime, SmallInteger, ForeignKey, JSON, func
from app.database import Base


class Rule(Base):
    __tablename__ = "museum_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="规则名称")
    code = Column(String(50), unique=True, comment="规则编码")
    description = Column(Text, comment="规则描述")
    rule_type = Column(String(50), comment="规则类型")
    rule_config = Column(JSON, comment="规则配置参数")
    enabled = Column(SmallInteger, default=1)
    created_at = Column(DateTime, server_default=func.now())


class RuleHit(Base):
    __tablename__ = "museum_rule_hit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("museum_event.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("museum_rule.id"), nullable=False)
    hit_time = Column(DateTime, nullable=False)
    confidence = Column(Float, comment="置信度")
    evidence_snapshot = Column(String(500), comment="证据截图")
    detail = Column(Text, comment="命中详情")
    created_at = Column(DateTime, server_default=func.now())
