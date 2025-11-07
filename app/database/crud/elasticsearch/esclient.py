from typing import Any, TypeVar, overload
from uuid import UUID, uuid4

from elastic_transport import ObjectApiResponse
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
G = TypeVar("G")


class ElasticsearchClient:
    def __init__(
        self,
        session: AsyncElasticsearch,
    ) -> None:
        self.session: AsyncElasticsearch = session

    async def __search(
        self,
        index: str,
        query: dict[str, Any],
    ) -> list[dict[str, Any]]:
        response: ObjectApiResponse[Any] = await self.session.search(
            index=index,
            body=query,
        )
        return [
            {"id": hit["_id"], **hit["_source"]} for hit in response["hits"]["hits"]
        ]

    async def __msearch(
        self,
        mquery: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], ...]:
        response: ObjectApiResponse[Any] = await self.session.msearch(searches=mquery)
        left: list[dict[str, Any]] = response["responses"][0]["hits"]["hits"]
        right: list[dict[str, Any]] = response["responses"][1]["hits"]["hits"]
        return left, right

    async def __get(
        self,
        index: str,
        id: UUID,
    ) -> dict[str, Any]:
        response: ObjectApiResponse[Any] = await self.session.get(
            index=index,
            id=str(id),
        )
        return response.body

    async def __add(
        self,
        index: str,
        instance: BaseModel,
    ) -> None:
        await self.session.create(
            index=index,
            id=str(uuid4()),
            document=instance.model_dump(),
        )

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
        await self.session.update(
            index=index,
            id=str(doc_id),
            body=update_body,
        )

    async def __delete(
        self,
        index: str,
        doc_id: UUID,
    ) -> None:
        await self.session.delete(
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
        **kwargs: Any,
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
