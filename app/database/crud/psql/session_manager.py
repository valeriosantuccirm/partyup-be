import traceback
import traceback as tback
from functools import wraps
from types import TracebackType
from typing import Any, Callable, Iterable, Tuple, Type, TypeVar

from asyncpg import PostgresError
from sqlalchemy import ColumnElement, Result, Select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import SQLModel, or_
from starlette import status

from app.api.exceptions.http_exc import DBException
from app.configlog import logger
from app.constants import DB_API_CONTEXT, DB_PSQL_DB_CONTEXT
from app.database.crud.meta import Meta

T = TypeVar("T", bound=SQLModel)


class PSQLTransactionMeta(metaclass=Meta):
    @classmethod
    def exc_handler(cls, func: Callable) -> Any:
        @wraps(wrapped=func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                rv: Any = await func(*args, **kwargs)
                return rv
            except (PostgresError, SQLAlchemyError) as e:
                logger.error(traceback.format_exc())
                raise DBException(
                    db_context=DB_PSQL_DB_CONTEXT,
                    detail=str(e),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return wrapper


class PSQLSessionManager(PSQLTransactionMeta):
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session: AsyncSession = session
        super().__init__()

    async def __aenter__(self) -> "PSQLSessionManager":
        return self

    async def __aexit__(
        self,
        type_: Type[BaseException] | None = None,
        value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        if type_:
            logger.error(f"Rolling back transaction due to: {type_.__name__}: {value}")
            if traceback:
                logger.error("Traceback (most recent call last):")
                logger.error("".join(tback.format_tb(tb=traceback)))
            await self.session.rollback()
            raise DBException(
                api_context=DB_API_CONTEXT,
                db_context=DB_PSQL_DB_CONTEXT,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        try:
            await self.session.flush()
            await self.session.commit()
        except (SQLAlchemyError, PostgresError) as e:
            await self.session.rollback()
            raise DBException(
                api_context=DB_API_CONTEXT,
                db_context=DB_PSQL_DB_CONTEXT,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )
        finally:
            await self.session.close()

    @PSQLTransactionMeta.exc_handler
    async def __add(
        self,
        instance: SQLModel,
    ) -> None:
        self.session.add(instance=instance)
        await self.session.flush()

    @PSQLTransactionMeta.exc_handler
    async def __delete(
        self,
        instance: SQLModel,
    ) -> None:
        await self.session.delete(instance=instance)
        await self.session.flush()

    @PSQLTransactionMeta.exc_handler
    async def __exe(
        self,
        q: Select[Tuple[T]],
    ) -> Result[Tuple[T]]:
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
        model: Type[T],
        criteria: Iterable[ColumnElement] = (),
        with_for_update: bool = False,
    ) -> T | None:
        query: Select[Tuple[T]] = select(model).filter(*criteria)
        if with_for_update:
            query = query.with_for_update()
        result: Result[Tuple[T]] = await self.__exe(q=query)
        return result.scalars().one_or_none()

    async def count(
        self,
        model: Type[T],
        clauses: Iterable[ColumnElement],
    ) -> int:
        query: Select[Tuple[int]] = (
            select(func.count()).select_from(model).where(or_(*clauses))
        )
        result: Result[Tuple[int]] = await self.__exe(q=query)
        count: int | None = result.scalar()
        return count if count else 0
