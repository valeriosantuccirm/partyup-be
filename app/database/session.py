import asyncio
from asyncio import AbstractEventLoop
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from app.config import settings
from app.database.crud.psql.session_manager import PSQLSessionManager

# Create session
engine: AsyncEngine = create_async_engine(url=settings.DB_URI, echo=True)

async_session_factory: sessionmaker[Session] = sessionmaker(
    engine,  # type: ignore[awaitable]
    class_=AsyncSession,
    expire_on_commit=False,
)


async def psql_session_manager() -> AsyncGenerator[PSQLSessionManager]:
    """
    Dependency that provides an async session to interact with the database.

    This function is used in FastAPI routes to manage the database session for
    the duration of the request and automatically handles session closing.

    Yields:
        AsyncSession: An async SQLAlchemy session to interact with the database.
    """
    async with async_session_factory() as session:  # pyright: ignore[reportGeneralTypeIssues]
        async with PSQLSessionManager(session=session) as db_session:
            yield db_session


def psql_session_manager_sync() -> PSQLSessionManager | None:
    loop: AbstractEventLoop = asyncio.get_event_loop()

    async def get_session() -> PSQLSessionManager | None:
        async for session in psql_session_manager():
            return session

    return loop.run_until_complete(future=get_session())
