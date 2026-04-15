from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.rule import Rule, RuleHit
from app.schemas.rule import RuleCreate, RuleUpdate, RuleOut
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user

router = APIRouter(prefix="/rules", tags=["规则管理"])


@router.get("")
async def list_rules(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    enabled: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(Rule)
    if enabled is not None:
        query = query.where(Rule.enabled == enabled)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(Rule.id.asc())
    result = await db.execute(query)
    items = [RuleOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.get("/{rule_id}")
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("规则不存在", 404)
    return ok(data=RuleOut.model_validate(rule))


@router.post("")
async def create_rule(body: RuleCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    rule = Rule(**body.model_dump())
    db.add(rule)
    await db.flush()
    await db.refresh(rule)
    return ok(data=RuleOut.model_validate(rule))


@router.put("/{rule_id}")
async def update_rule(rule_id: int, body: RuleUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("规则不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    await db.flush()
    await db.refresh(rule)
    return ok(data=RuleOut.model_validate(rule))


@router.put("/{rule_id}/toggle")
async def toggle_rule(rule_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("规则不存在", 404)
    rule.enabled = 0 if rule.enabled == 1 else 1
    await db.flush()
    return ok(data=RuleOut.model_validate(rule))


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        return fail("规则不存在", 404)
    await db.delete(rule)
    return ok(message="删除成功")


@router.get("/stats/hit-counts")
async def rule_hit_stats(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    """每条规则的命中次数统计"""
    query = (
        select(RuleHit.rule_id, func.count().label("hit_count"))
        .group_by(RuleHit.rule_id)
    )
    rows = (await db.execute(query)).all()
    hit_map = {r.rule_id: r.hit_count for r in rows}

    rules_result = await db.execute(select(Rule).order_by(Rule.id.asc()))
    result = [
        {"rule_id": rule.id, "rule_name": rule.name, "code": rule.code, "hit_count": hit_map.get(rule.id, 0)}
        for rule in rules_result.scalars().all()
    ]
    return ok(data=result)
