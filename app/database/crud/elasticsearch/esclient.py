import traceback
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, overload
from uuid import UUID, uuid4

from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ApiError
from pydantic import BaseModel

from app.api.exceptions.http_exc import DBException
from app.config import settings
from app.configlog import logger
from app.constants import DB_ES_DB_CONTEXT
from app.database.crud.meta import Meta

T = TypeVar("T", bound=BaseModel)
G = TypeVar("G")


class ElasticsearchMeta(metaclass=Meta):
    _es: AsyncElasticsearch | None = None

    @classmethod
    async def init_client(cls) -> None:
        if not cls._es:
            cls._es = AsyncElasticsearch(hosts=[settings.ES_URI])

    @classmethod
    async def close_client(cls) -> None:
        if cls._es:
            await cls._es.close()
            cls._es = None

    @property
    def es(cls) -> AsyncElasticsearch:
        if not cls._es:
            cls._es = AsyncElasticsearch(hosts=[settings.ES_URI])
        return cls._es

    @classmethod
    def exc_handler(cls, func: Callable[..., Any]) -> Any:
        @wraps(wrapped=func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                rv: Any = await func(*args, **kwargs)
                return rv
            except ApiError as e:
                logger.error(traceback.format_exc())
                raise DBException(
                    db_context=DB_ES_DB_CONTEXT,
                    status_code=e.status_code,
                    detail=e.info,
                ) from e

        return wrapper


class ElasticsearchClient(ElasticsearchMeta):
    def __init__(
        self,
    ) -> None:
        super().__init__()

    @ElasticsearchMeta.exc_handler
    async def __search(
        self,
        index: str,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        response: ObjectApiResponse[Any] = await self.es.search(
            index=index,
            body=query,
        )
        return [
            {"id": hit["_id"], **hit["_source"]} for hit in response["hits"]["hits"]
        ]

    @ElasticsearchMeta.exc_handler
    async def __msearch(
        self,
        mquery: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], ...]:
        response: ObjectApiResponse[Any] = await self.es.msearch(searches=mquery)
        left: list[dict[str, Any]] = response["responses"][0]["hits"]["hits"]
        right: list[dict[str, Any]] = response["responses"][1]["hits"]["hits"]
        return left, right

    @ElasticsearchMeta.exc_handler
    async def __get(
        self,
        index: str,
        id: UUID,
    ) -> dict[str, Any]:
        response: ObjectApiResponse[Any] = await self.es.get(
            index=index,
            id=str(id),
        )
        return response.body

    @ElasticsearchMeta.exc_handler
    async def __add(
        self,
        index: str,
        instance: BaseModel,
    ) -> None:
        await self.es.create(
            index=index,
            id=str(uuid4()),
            document=instance.model_dump(),
        )

    @ElasticsearchMeta.exc_handler
    async def __update(
        self,
        index: str,
        doc_id: UUID,
        **kwargs: Any,
    ) -> None:
        update_body: dict[str, Any] = {
            "doc": {
                **kwargs,
            },
        }
        await self.es.update(
            index=index,
            id=str(doc_id),
            body=update_body,
        )

    @ElasticsearchMeta.exc_handler
    async def __delete(
        self,
        index: str,
        doc_id: UUID,
    ) -> None:
        await self.es.delete(
            index=index,
            id=str(object=doc_id),
        )

    @overload
    async def find(
        self, index: str, query: dict[str, Any], model: type[T]
    ) -> list[T]: ...

    @overload
    async def find(
        self, index: str, query: dict[str, Any], model: type[T], one: bool
    ) -> T | None: ...

    async def find(
        self,
        index: str,
        query: dict[str, Any],
        model: type[T],
        one: bool = False,
    ) -> list[T] | T | None:
        results: list[dict[str, Any]] = await self.__search(index=index, query=query)
        instances = []
        instances: list[T] = [
            model(**r) for r in results
        ]  # TODO: use model_construct to boost performance
        if one:
            return next(iter(instances), None)
        return instances

    async def get(
        self,
        index: str,
        id: UUID,
        model: type[T],
    ) -> T:
        result: dict[str, Any] = await self.__get(index=index, id=id)
        return model(**result["_source"], id=result["_id"])

    async def update(
        self,
        index: str,
        doc_id: UUID,
        **kwargs: dict[str, Any],
    ) -> None:
        await self.__update(index=index, doc_id=doc_id, **kwargs)

    async def add(
        self,
        index: str,
        instance: BaseModel,
    ) -> None:
        await self.__add(index=index, instance=instance)

    async def delete(
        self,
        index: str,
        doc_id: UUID,
    ) -> None:
        await self.__delete(index=index, doc_id=doc_id)

    async def msearch(
        self,
        mquery: list[dict[str, Any]],
    ) -> tuple[G, G]:
        return await self.__msearch(mquery=mquery)
