"""通用 CRUD 基类，减少 rooms/cameras/collections/rules 的重复代码"""
from typing import Type, TypeVar, Optional, List
from fastapi import Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from app.database import Base, get_db
from app.schemas.common import ok, PageResult

ModelType = TypeVar("ModelType", bound=Base)
CreateSchema = TypeVar("CreateSchema", bound=BaseModel)
UpdateSchema = TypeVar("UpdateSchema", bound=BaseModel)
OutSchema = TypeVar("OutSchema", bound=BaseModel)


class CRUDBase:
    """通用 CRUD 路由工厂"""

    def __init__(self, model: Type[Base], out_schema: Type[BaseModel], name: str):
        self.model = model
        self.out_schema = out_schema
        self.name = name

    async def list_items(
        self,
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        filters: Optional[list] = None,
    ):
        query = select(self.model)
        if filters:
            for f in filters:
                query = query.where(f)
        total_q = select(func.count()).select_from(query.subquery())
        total = (await db.execute(total_q)).scalar() or 0
        query = query.offset((page - 1) * size).limit(size).order_by(self.model.id.desc())
        result = await db.execute(query)
        items = [self.out_schema.model_validate(r) for r in result.scalars().all()]
        return ok(data=PageResult(items=items, total=total, page=page, size=size))

    async def get_item(self, db: AsyncSession, item_id: int):
        result = await db.execute(select(self.model).where(self.model.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail=f"{self.name}不存在")
        return ok(data=self.out_schema.model_validate(item))

    async def create_item(self, db: AsyncSession, body: BaseModel):
        item = self.model(**body.model_dump())
        db.add(item)
        await db.flush()
        await db.refresh(item)
        return ok(data=self.out_schema.model_validate(item))

    async def update_item(self, db: AsyncSession, item_id: int, body: BaseModel):
        result = await db.execute(select(self.model).where(self.model.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail=f"{self.name}不存在")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
        await db.flush()
        await db.refresh(item)
        return ok(data=self.out_schema.model_validate(item))

    async def delete_item(self, db: AsyncSession, item_id: int):
        result = await db.execute(select(self.model).where(self.model.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail=f"{self.name}不存在")
        await db.delete(item)
        return ok(message="删除成功")
