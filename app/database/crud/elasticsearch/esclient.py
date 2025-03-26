import traceback
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar, overload
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
    def exc_handler(cls, func: Callable) -> Any:
        @wraps(wrapped=func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                rv: Any = await func(*args, **kwargs)
                return rv
            except ApiError as e:
                logger.error(traceback.format_exc())
                raise DBException(
                    db_context=DB_ES_DB_CONTEXT,
                    status_code=e.status_code,
                    detail=e.info,
                )

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
        query: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
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
        mquery: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], ...]:
        response: ObjectApiResponse[Any] = await self.es.msearch(searches=mquery)
        left: List[Dict[str, Any]] = response["responses"][0]["hits"]["hits"]
        right: List[Dict[str, Any]] = response["responses"][1]["hits"]["hits"]
        return left, right

    @ElasticsearchMeta.exc_handler
    async def __get(
        self,
        index: str,
        id: UUID,
    ) -> Dict[str, Any]:
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
        **kwargs,
    ) -> None:
        update_body: Dict[str, Any] = {
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
        self, index: str, query: Dict[str, Any], model: Type[T]
    ) -> List[T]: ...

    @overload
    async def find(
        self, index: str, query: Dict[str, Any], model: Type[T], one: bool
    ) -> T | None: ...

    async def find(
        self,
        index: str,
        query: Dict[str, Any],
        model: Type[T],
        one: bool = False,
    ) -> List[T] | T | None:
        results: List[Dict[str, Any]] = await self.__search(index=index, query=query)
        instances = []
        instances: List[T] = [
            model(**r) for r in results
        ]  # TODO: use model_construct to boost performance
        if one:
            return next(iter(instances), None)
        return instances

    async def get(
        self,
        index: str,
        id: UUID,
        model: Type[T],
    ) -> T:
        result: Dict[str, Any] = await self.__get(index=index, id=id)
        return model(**result["_source"], id=result["_id"])

    async def update(
        self,
        index: str,
        doc_id: UUID,
        **kwargs,
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
        mquery: List[Dict[str, Any]],
    ) -> Tuple[G, G]:
        return await self.__msearch(mquery=mquery)
