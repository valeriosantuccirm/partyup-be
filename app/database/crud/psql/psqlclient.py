from collections.abc import Iterable, Sequence
from typing import Any, TypeVar

from sqlalchemy import ColumnElement, Result, Select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import SQLModel, or_

T = TypeVar("T", bound=SQLModel)


class PSQLClient:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session: AsyncSession = session

    async def __add(
        self,
        instance: SQLModel,
    ) -> None:
        self.session.add(instance=instance)
        await self.session.flush()

    async def __delete(
        self,
        instance: SQLModel,
    ) -> None:
        await self.session.delete(instance=instance)
        await self.session.flush()

    async def __exe(
        self,
        q: Select[tuple[T]],
    ) -> Result[tuple[T]]:
        return await self.session.execute(statement=q)

    async def add(
        self,
        instance: SQLModel,
    ) -> None:
        await self.__add(
            instance=instance,
        )

    async def update(
        self,
        instance: SQLModel,
    ) -> None:
        await self.__add(
            instance=instance,
        )

    async def delete(
        self,
        instance: SQLModel,
    ) -> None:
        await self.__delete(
            instance=instance,
        )

    async def find_one_or_none(
        self,
        model: type[T],
        criteria: Iterable[ColumnElement[Any]] = (),
        with_for_update: bool = False,
    ) -> T | None:
        query: Select[tuple[T]] = select(model).filter(*criteria)
        if with_for_update:
            query = query.with_for_update()
        result: Result[tuple[T]] = await self.__exe(q=query)
        return result.scalars().one_or_none()

    async def count(
        self,
        model: type[T],
        clauses: Iterable[ColumnElement[Any]],
    ) -> int:
        query: Select[tuple[int]] = (
            select(func.count()).select_from(model).where(or_(*clauses))
        )
        result: Result[tuple[int]] = await self.__exe(q=query)  # type: ignore
        count: int | None = result.scalar()
        return count if count else 0

    async def get_all(
        self,
        model: type[T],
        criteria: Iterable[ColumnElement[Any]] = (),
    ) -> Sequence[T]:
        query: Select[tuple[T]] = select(model).filter(*criteria)
        result: Result[tuple[T]] = await self.__exe(q=query)
        return result.scalars().all()
