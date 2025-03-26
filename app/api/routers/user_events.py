import json
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Form, Path, Query, UploadFile
from pydantic import StrictStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import user_events
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_event import ESEvent, ESEventBase
from app.database.models.enums.event import EventStatus
from app.database.models.psql.event import Event
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.request import (
    EventCreateExtendedRequest,
    EventCreateRequest,
    UserEventUpdateExtendedRequest,
    UserEventUpdateRequest,
)
from app.depends.depends import admit_user, get_es_query_service

router = APIRouter(prefix="/users/me/events")


@router.post(
    path="/create",
    response_model=Event,
    status_code=status.HTTP_201_CREATED,
    description="Create a new event with optional cover image.",
)
async def create_event(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_request: Annotated[
        StrictStr,
        Form(
            default=...,
            media_type="application/json",
            examples=EventCreateRequest.examples(),
        ),
    ],
    cover_image: Annotated[UploadFile | None, File(default=...)] = None,
) -> Event:
    """
    Create a new event.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        event_request (StrictStr): JSON string containing event details.
        cover_image (UploadFile | None): Optional cover image for the event.

    Returns:
        Event: The newly created event.
    """
    event_body = EventCreateExtendedRequest(
        **json.loads(s=event_request),
        cover_image=cover_image,
    )
    return await user_events.create_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_request=event_body,
    )


@router.get(
    path="",
    response_model=List[ESEventBase],
    status_code=status.HTTP_200_OK,
    description="Retrieve a list of events for the logged-in user.",
)
async def get_events(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    user: Annotated[User, Depends(dependency=admit_user)],
    status: Annotated[EventStatus | None, Query(default=...)] = None,
) -> List[ESEvent]:
    """
    Retrieve events for the logged-in user.

    Args:
        user (User): The authenticated user.
        status (EventStatus | None): Optional filter for event status.

    Returns:
        List[ESEvent]: A list of events matching the criteria.
    """
    return await user_events.get_user_events(
        esclient=esclient,
        user=user,
        status=status,
    )


@router.delete(
    path="/{event_guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Cancel an event created by the logged-in user.",
)
async def cancel_event(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_guid: Annotated[UUID, Path(default=...)],
) -> None:
    """
    Cancel an event.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        event_guid (UUID): The unique ID of the event to cancel.

    Returns:
        None
    """
    return await user_events.cancel_user_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )


@router.patch(
    path="/{event_guid}",
    status_code=status.HTTP_200_OK,
    description="Update an existing event's details and/or cover image.",
    response_model=Event,
)
async def update_event(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_guid: Annotated[UUID, Path(default=...)],
    event_request: Annotated[
        StrictStr,
        Form(
            default=...,
            media_type="application/json",
            examples=UserEventUpdateRequest.examples(),
        ),
    ],
    cover_image: Annotated[UploadFile | None, File(default=...)] = None,
    replace_cover_image: Annotated[bool, Query(default=...)] = False,
) -> Event:
    """
    Update an existing event.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        event_guid (UUID): The unique ID of the event to update.
        event_request (StrictStr): JSON string containing updated event details.
        cover_image (UploadFile | None): Optional new cover image.
        replace_cover_image (bool): If True, replaces the existing cover image.

    Returns:
        Event: The updated event.
    """
    event_body = UserEventUpdateExtendedRequest(
        **json.loads(s=event_request),
        cover_image=cover_image,
    )
    return await user_events.update_user_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
        event_request=event_body,
        replace_cover_image=replace_cover_image,
    )


@router.post(
    path="/{event_guid}/send-invitation",
    status_code=status.HTTP_201_CREATED,
    description="Send event invitations to selected hivers.",
)
async def send_event_invitations_to_hivers(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_guid: Annotated[UUID, Path(default=...)],
    hivers_guids: Annotated[List[UUID], Body(default=...)],
) -> None:
    await user_events.send_event_invitations_to_hivers(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
        hivers_guids=hivers_guids,
    )


@router.put(
    path="/{event_guid}/rsvp",
    status_code=status.HTTP_204_NO_CONTENT,
    description="RSVP to an event by accepting or decline a join request.",
)
async def rsvp_to_event_join_request(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    event_guid: Annotated[UUID, Path(default=...)],
    accept: Annotated[bool, Query(default=...)],
) -> None:
    await user_events.rsvp_event_participation(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
        accept=accept,
    )
