from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.inventory import InventoryCheck, CollectionMovement
from app.models.collection import Collection
from app.schemas.inventory import (
    InventoryCheckCreate, InventoryCheckUpdate, InventoryCheckOut,
    MovementCreate, MovementOut,
)
from app.schemas.common import ok, fail, PageResult
from app.utils.deps import get_current_user
import csv
import io

router = APIRouter(prefix="/inventory", tags=["盘点与进出库"])


# ── 盘点记录 ──────────────────────────────────────────────

@router.get("/checks")
async def list_checks(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    room_id: int = Query(None),
    status: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(InventoryCheck)
    if room_id is not None:
        query = query.where(InventoryCheck.room_id == room_id)
    if status is not None:
        query = query.where(InventoryCheck.status == status)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(InventoryCheck.id.desc())
    result = await db.execute(query)
    items = [InventoryCheckOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.post("/checks")
async def create_check(body: InventoryCheckCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    record = InventoryCheck(**body.model_dump())
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return ok(data=InventoryCheckOut.model_validate(record))


@router.put("/checks/{check_id}")
async def update_check(check_id: int, body: InventoryCheckUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(InventoryCheck).where(InventoryCheck.id == check_id))
    record = result.scalar_one_or_none()
    if not record:
        return fail("盘点记录不存在", 404)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(record, k, v)
    await db.flush()
    await db.refresh(record)
    return ok(data=InventoryCheckOut.model_validate(record))


@router.delete("/checks/{check_id}")
async def delete_check(check_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(InventoryCheck).where(InventoryCheck.id == check_id))
    record = result.scalar_one_or_none()
    if not record:
        return fail("盘点记录不存在", 404)
    await db.delete(record)
    return ok(message="删除成功")


@router.get("/checks/{check_id}/export")
async def export_check(check_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(InventoryCheck).where(InventoryCheck.id == check_id))
    record = result.scalar_one_or_none()
    if not record:
        return fail("盘点记录不存在", 404)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["盘点ID", "库房ID", "盘点日期", "应盘数量", "已盘数量", "一致数量", "不一致数量", "状态", "操作人", "备注"])
    writer.writerow([
        record.id, record.room_id, str(record.check_date),
        record.total_count, record.checked_count, record.matched_count,
        record.mismatched_count, "已完成" if record.status == 1 else "进行中",
        record.operator or "", record.remark or "",
    ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventory_check_{check_id}.csv"},
    )


# ── 进出库记录 ──────────────────────────────────────────────

@router.get("/movements")
async def list_movements(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    collection_id: int = Query(None),
    movement_type: int = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_user),
):
    query = select(CollectionMovement)
    if collection_id is not None:
        query = query.where(CollectionMovement.collection_id == collection_id)
    if movement_type is not None:
        query = query.where(CollectionMovement.movement_type == movement_type)
    total_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(total_q)).scalar() or 0
    query = query.offset((page - 1) * size).limit(size).order_by(CollectionMovement.id.desc())
    result = await db.execute(query)
    items = [MovementOut.model_validate(r) for r in result.scalars().all()]
    return ok(data=PageResult(items=items, total=total, page=page, size=size))


@router.post("/movements")
async def create_movement(body: MovementCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    # 验证藏品存在
    coll_result = await db.execute(select(Collection).where(Collection.id == body.collection_id))
    coll = coll_result.scalar_one_or_none()
    if not coll:
        return fail("藏品不存在", 404)

    record = CollectionMovement(**body.model_dump())
    db.add(record)

    # 同步更新藏品状态
    if body.movement_type == 1:
        coll.status = 1  # 入库
        if body.room_id:
            coll.room_id = body.room_id
    elif body.movement_type == 2:
        coll.status = 2  # 出库

    await db.flush()
    await db.refresh(record)
    return ok(data=MovementOut.model_validate(record))
