from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Path, Query, UploadFile
from pydantic import StrictStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import events
from app.core.decorators import manage_transaction
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.enums.event import EventStatus
from app.database.models.psql.media import Media
from app.database.models.psql.user import User
from app.database.session import esclient, psqlclient
from app.datamodels.schemas.response import PaginatedEvents
from app.depends.depends import admit_user, get_attendee

router = APIRouter(prefix="/events")


@router.get(
    path="/leaderboard",
    response_model=PaginatedEvents,
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def get_leaderboard_events(
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
    esclient: Annotated[ElasticsearchClient, Depends(dependency=esclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    lat: Annotated[float, Query(default=...)],
    lon: Annotated[float, Query(default=...)],
    radius: Annotated[int, Query(default=...)] = 50,
    status: Annotated[EventStatus, Query(default=...)] = EventStatus.UPCOMING,
    limit: Annotated[int, Query(default=...)] = 10,
    offset: Annotated[int, Query(default=...)] = 0,
) -> PaginatedEvents:
    """
    Retrieve a paginated list of leaderboard events based on the user's location and preferences.

    Args:
        lat (float): Latitude of the user's location for proximity-based event ranking.
        lon (float): Longitude of the user's location for proximity-based event ranking.
        radius (int, optional): Search radius in kilometers (default is 10).
        status (EventStatus, optional): Filter events based on status (default is 'UPCOMING').
        limit (int, optional): Number of events to return (default is 10).
        offset (int, optional): Pagination offset (default is 0).

    Returns:
        PaginatedEvents: A paginated list of leaderboard events.
    """
    return await events.get_leaderboard_events(
        esclient=esclient,
        user=user,
        lat=lat,
        lon=lon,
        status=status,
        radius=radius,
        limit=limit,
        offset=offset,
    )


@router.get(
    path="/search",
    response_model=PaginatedEvents,
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def search_events(
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
    esclient: Annotated[ElasticsearchClient, Depends(dependency=esclient)],
    user: Annotated[User, Depends(dependency=admit_user)],
    lat: Annotated[float, Query(default=...)],
    lon: Annotated[float, Query(default=...)],
    q: Annotated[StrictStr, Query(default=...)],
    radius: Annotated[int, Query(default=...)] = 10,
    status: Annotated[EventStatus, Query(default=...)] = EventStatus.UPCOMING,
    limit: Annotated[int, Query(default=...)] = 10,
    offset: Annotated[int, Query(default=...)] = 0,
) -> PaginatedEvents:
    """
    Search for events based on location and user input, with optional status and pagination filters.

    Args:
        lat (float): Latitude of the user's location for proximity-based search.
        lon (float): Longitude of the user's location for proximity-based search.
        q (StrictStr): Search query, such as event keywords or titles.
        radius (int, optional): Search radius in kilometers (default is 10).
        status (EventStatus, optional): Filter events based on status (default is 'UPCOMING').
        limit (int, optional): Maximum number of events to return (default is 10).
        offset (int, optional): Pagination offset (default is 0).

    Returns:
        PaginatedEvents: A paginated list of events that match the search criteria.
    """
    return await events.search_events(
        esclient=esclient,
        user=user,
        lat=lat,
        lon=lon,
        status=status,
        radius=radius,
        user_input=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    path="/events/{event_guid}/media",
    response_model=Media,
    status_code=status.HTTP_201_CREATED,
)
@manage_transaction
async def upload_event_media(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=esclient)],
    event_guid: Annotated[UUID, Path(default=...)],
    file: Annotated[UploadFile, File(default=...)],
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=get_attendee)],
) -> Media:
    """
    Uploads a media file (image/video) for an event.
    Stores it in S3, saves metadata in PostgreSQL, and updates Elasticsearch.
    """
    return await events.upload_user_event_media(
        esclient=esclient,
        db_session=db_session,
        user=user,
        media_content=file,
        event_guid=event_guid,
    )


@router.put(
    path="/events/{event_guid}/join",
    status_code=status.HTTP_204_NO_CONTENT,
)
@manage_transaction
async def join_public_event(
    event_guid: Annotated[UUID, Path(default=...)],
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=get_attendee)],
) -> None:
    return await events.join_public_event(
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )


@router.delete(
    path="/events/{event_guid}/revoke-join",
    status_code=status.HTTP_204_NO_CONTENT,
)
@manage_transaction
async def revoke_join_public_event(
    event_guid: Annotated[UUID, Path(default=...)],
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=get_attendee)],
) -> None:
    return await events.revoke_join_event(
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )


@router.put(
    path="/qrcode/aknowledge",
    status_code=status.HTTP_200_OK,
)
@manage_transaction
async def read_event_generated_qrcode(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    _: Annotated[User, Depends(dependency=get_attendee)],
    token: Annotated[str, Body(default=...)],
) -> Any:
    return await events.aknowledge_data_by_scanned_qr_code(
        db_session=db_session,
        token=token,
    )
