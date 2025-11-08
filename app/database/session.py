from collections.abc import AsyncGenerator
from typing import Any

from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.config import settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.psqlclient import PSQLClient

# Create Postgre session
engine: AsyncEngine = create_async_engine(url=settings.DB_URI, echo=True)

async_session_factory: sessionmaker[Session] = sessionmaker(
    engine,  # type: ignore[awaitable]
    class_=AsyncSession,
    expire_on_commit=False,
)


async def psqlclient() -> AsyncGenerator[PSQLClient, Any]:
    async with async_session_factory() as session:  # type: ignore
        yield PSQLClient(
            session=session,  # type: ignore
        )


async def esclient() -> AsyncGenerator[ElasticsearchClient, Any]:
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        yield ElasticsearchClient(
            session=session,
        )
