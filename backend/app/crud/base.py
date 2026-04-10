from __future__ import annotations

from typing import Any, Generic, TypeVar, Optional

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.loguru_config import logger

ModelType = TypeVar("ModelType")


class CRUDBase(Generic[ModelType]):
    """
    泛型异步 CRUD 基类。
    使用 SQLAlchemy 2.0 风格的 select API。
    """

    model: type[ModelType]

    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, pk: int) -> Optional[ModelType]:
        """通过主键获取单条记录。"""
        pk_field = self.model.__table__.primary_key.columns.values()
        if not pk_field:
            raise ValueError(f"Model {self.model.__name__} has no primary key")
        pk_field = pk_field[0]
        result = await self.session.execute(select(self.model).where(pk_field == pk))
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
    ) -> list[ModelType]:
        """获取多条记录，支持分页和排序。"""
        query = select(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_column(self, **filters: Any) -> Optional[ModelType]:
        """通过任意列条件查询单条记录。"""
        query = select(self.model)
        for column, value in filters.items():
            query = query.where(getattr(self.model, column) == value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_multi_by_column(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
        **filters: Any,
    ) -> list[ModelType]:
        """通过任意列条件查询多条记录。"""
        query = select(self.model)
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """创建单条记录。"""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj

    async def create_many(self, objects: list[dict[str, Any]]) -> list[ModelType]:
        """批量创建记录。"""
        db_objs = [self.model(**obj) for obj in objects]
        self.session.add_all(db_objs)
        await self.session.flush()
        return db_objs

    async def update(
        self,
        pk: int,
        obj_in: dict[str, Any],
    ) -> Optional[ModelType]:
        """更新单条记录。"""
        db_obj = await self.get(pk)
        if db_obj is None:
            return None
        for key, value in obj_in.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        await self.session.flush()
        return db_obj

    async def upsert(
        self,
        unique_fields: dict[str, Any],
        obj_in: dict[str, Any],
    ) -> tuple[ModelType, bool]:
        """
        插入或更新记录。
        unique_fields: 用于查询已存在记录的字段条件。
        返回 (db_obj, created)。
        """
        existing = await self.get_by_column(**unique_fields)
        if existing:
            for key, value in obj_in.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await self.session.flush()
            return existing, False

        db_obj = self.model(**{**unique_fields, **obj_in})
        self.session.add(db_obj)
        await self.session.flush()
        return db_obj, True

    async def remove(self, pk: int) -> bool:
        """删除单条记录。"""
        db_obj = await self.get(pk)
        if db_obj is None:
            return False
        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def delete_by_column(self, **filters: Any) -> int:
        """通过条件删除多条记录，返回删除数量。"""
        query = delete(self.model)
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        result = await self.session.execute(query)
        return result.rowcount

    async def exists(self, **filters: Any) -> bool:
        """检查记录是否存在。"""
        query = select(self.model).limit(1)
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def count(self, **filters: Any) -> int:
        """统计记录数量。"""
        query = select(func.count()).select_from(self.model)
        for column, value in filters.items():
            if hasattr(self.model, column):
                query = query.where(getattr(self.model, column) == value)
        result = await self.session.execute(query)
        return result.scalar() or 0


class CRUDPaged(CRUDBase[ModelType]):
    """支持分页的 CRUD。"""

    async def get_page(
        self,
        page: int = 1,
        page_size: int = 24,
        order_by: Optional[Any] = None,
        **filters: Any,
    ) -> tuple[list[ModelType], int]:
        """
        分页获取记录。
        返回 (items, total_count)。
        """
        skip = (page - 1) * page_size

        count_query = select(func.count()).select_from(self.model)
        for column, value in filters.items():
            if hasattr(self.model, column):
                count_query = count_query.where(getattr(self.model, column) == value)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        data_query = select(self.model)
        for column, value in filters.items():
            if hasattr(self.model, column):
                data_query = data_query.where(getattr(self.model, column) == value)
        if order_by is not None:
            data_query = data_query.order_by(order_by)
        data_query = data_query.offset(skip).limit(page_size)

        result = await self.session.execute(data_query)
        return list(result.scalars().all()), total
