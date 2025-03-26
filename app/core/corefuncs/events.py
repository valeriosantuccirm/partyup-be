import json
from typing import Any, Dict, List
from uuid import UUID

from fastapi import Depends, UploadFile
from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import settings
from app.constants import (
    DB_API_CONTEXT,
    DB_ES_DB_CONTEXT,
    DB_PSQL_DB_CONTEXT,
    PUB_EVENT_API_CONTEXT,
)
from app.core import common, fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q, events_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.elasticsearch.es_event_attendee import (
    ESEventAttendee,
    ESEventAttendeeBase,
)
from app.database.models.elasticsearch.es_media import ESMediaBase
from app.database.models.enums.event import (
    AttendeeType,
    EventAttendeeStatus,
    EventStatus,
)
from app.database.models.enums.media import MediaType
from app.database.models.psql.event import Event
from app.database.models.psql.event_attendee import EventAttendee
from app.database.models.psql.media import Media
from app.database.models.psql.user import User
from app.database.models.psql.user_follower import UserFollower
from app.database.redis import RedisClient
from app.datamodels.schemas.response import PaginatedEvents
from app.depends.depends import get_redis_client


async def get_leaderboard_events(
    esclient: ElasticsearchClient,
    user: User,
    lat: float,
    lon: float,
    status: EventStatus,
    radius: int,
    limit: int = 10,
    offset: int = 0,
) -> PaginatedEvents:
    q: Dict[str, Any] = events_q.build_leaderboard_events(
        creator_guid=user.guid,
        status=status,
        user_bio=user.bio,
        user_lat=lat,
        user_lon=lon,
        radius=radius,
        limit=limit,
        offset=offset,
    )
    events: List[ESEvent] = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=q,
        model=ESEvent,
    )
    return PaginatedEvents(
        events=events,
        total_results=len(events),
        limit=limit,
        offset=offset,
    )


async def search_events(
    esclient: ElasticsearchClient,
    user: User,
    lat: float,
    lon: float,
    status: EventStatus,
    radius: int,
    user_input: str,
    limit: int = 10,
    offset: int = 0,
) -> PaginatedEvents:
    q: Dict[str, Any] = events_q.search_events(
        creator_guid=user.guid,
        status=status,
        user_input=user_input,
        user_bio=user.bio,
        user_lat=lat,
        user_lon=lon,
        user_location_name=user.location_name,
        radius=radius,
        limit=limit,
        offset=offset,
    )
    events: List[ESEvent] = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=q,
        model=ESEvent,
    )
    return PaginatedEvents(
        events=events,
        total_results=len(events),
        limit=limit,
        offset=offset,
    )


async def upload_user_event_media(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    media_content: UploadFile,
    event_guid: UUID,
    redis_client: RedisClient = Depends(dependency=get_redis_client),
) -> Media:
    event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not event or event.status not in (
        EventStatus.ONGOING,
        EventStatus.OUTDATED,
    ):
        raise APIException(
            api_context=PUB_EVENT_API_CONTEXT,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Event with guid '{event_guid}' not found or not ready to host media content",
        )
    ext: str = await common.get_file_extension(
        media_filename=media_content.filename,
    )
    file_url, content_filename = await common.upload_content_to_s3(
        media_content=media_content,
        dirpath="event-media",
        ext=ext,
    )
    psql_media = Media(
        event_guid=event_guid,
        file_url=file_url,
        media_type=MediaType.PHOTO,  # TODO: create class to get media type (enum)/ extension etc
        user_guid=user.guid,
        content_filename=content_filename,
    )
    await db_session.add(
        instance=psql_media,
    )
    es_media = ESMediaBase(**psql_media.model_dump())
    await esclient.add(
        index=settings.ES_MEDIA_INDEX,
        instance=es_media,
    )
    # ✅ **Publish the event update to Redis**
    redis_channel: str = f"event_media:{event_guid}"
    redis_message = {
        "event_guid": str(event_guid),
        "user_guid": str(user.guid),
        "file_url": file_url,
        "media_type": MediaType.PHOTO.value,
    }
    redis_client = await get_redis_client()
    await redis_client.redis.publish(
        channel=redis_channel, message=json.dumps(redis_message)
    )
    return psql_media


async def join_public_event(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
) -> None:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event or psql_event.status != EventStatus.UPCOMING:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' not found in PSQL or status is not 'UPCOMING'",
        )
    if psql_event.total_attendees_count == psql_event.max_attendees:
        raise APIException(
            api_context=PUB_EVENT_API_CONTEXT,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' has reached the maximum number of attendees",
        )
    es_event: ESEvent | None = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=common_q.find_by_attr(guid=event_guid),
        model=ESEvent,
        one=True,
    )
    if not es_event:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with guid '{event_guid}' not found in ES",
        )
    psql_event.total_attendees_count += 1
    attendee_type: AttendeeType = AttendeeType.PUBLIC
    is_follower: int = await db_session.count(
        model=UserFollower,
        clauses=(
            Column("follower_guid") == user.guid,
            Column("user_guid") == psql_event.creator_guid,
        ),
    )
    if is_follower > 0:
        attendee_type = AttendeeType.FOLLOWER
        psql_event.followers_attendees_count += 1
    else:
        attendee_type = AttendeeType.PUBLIC
        psql_event.public_attendees_count += 1
    event_attendee = EventAttendee(
        attendee_type=attendee_type,
        event_guid=event_guid,
        user_guid=user.guid,
        status=EventAttendeeStatus.CONFIRMED,
    )
    await db_session.add(
        instance=event_attendee,
    )
    creator: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == psql_event.creator_guid,),
    )
    if not creator:
        raise APIException(
            api_context=PUB_EVENT_API_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{psql_event.creator_guid}' not found",
        )
    await esclient.add(
        index=settings.ES_EVENT_ATTENDEES_INDEX,
        instance=ESEventAttendeeBase(**event_attendee.model_dump()),
    )
    await esclient.update(
        index=settings.ES_EVENTS_INDEX,
        doc_id=es_event.id,
        total_attendees_count=psql_event.total_attendees_count,
        followers_attendees_count=psql_event.followers_attendees_count,
    )
    if creator.fcm_token:
        await fcm.send_push_notification(
            fcm_token=creator.fcm_token,
            title="New event joiner!",
            body=f"{user.username} will join your event",
            image_url=psql_event.cover_image_url,
        )


async def revoke_join_event(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
) -> None:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event or psql_event.status != EventStatus.UPCOMING:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' not found in PSQL or status is not 'UPCOMING'",
        )
    es_event: ESEvent | None = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=common_q.find_by_attr(guid=event_guid),
        model=ESEvent,
        one=True,
    )
    if not es_event:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with guid '{event_guid}' not found in ES",
        )
    psql_event_attendee: EventAttendee | None = await db_session.find_one_or_none(
        model=EventAttendee,
        criteria=(
            Column("event_guid") == event_guid,
            Column("user_guid") == user.guid,
        ),
    )
    if not psql_event_attendee:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{user.guid}' not found in event with guid '{event_guid}' in PSQL",
        )
    es_event_attendee: ESEventAttendee | None = await esclient.find(
        index=settings.ES_EVENT_ATTENDEES_INDEX,
        query=common_q.find_by_attr(guid=psql_event_attendee.guid),
        model=ESEventAttendee,
        one=True,
    )
    if not es_event_attendee:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{user.guid}' not found in event with guid '{event_guid}' in ES",
        )
    psql_event.total_attendees_count -= 1
    creator: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == psql_event.creator_guid,),
    )
    if not creator:
        raise APIException(
            api_context=PUB_EVENT_API_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{psql_event.creator_guid}' not found",
        )
    is_follower: int = await db_session.count(
        model=UserFollower,
        clauses=(
            Column("follower_guid") == user.guid,
            Column("user_guid") == psql_event.creator_guid,
        ),
    )
    if is_follower > 0:
        psql_event.followers_attendees_count -= 1
    else:
        psql_event.public_attendees_count -= 1
    await db_session.delete(
        instance=psql_event_attendee,
    )
    await esclient.delete(
        index=settings.ES_EVENT_ATTENDEES_INDEX,
        doc_id=es_event_attendee.id,
    )
    await esclient.update(
        index=settings.ES_EVENTS_INDEX,
        doc_id=es_event.id,
        total_attendees_count=psql_event.total_attendees_count,
        followers_attendees_count=psql_event.followers_attendees_count,
    )
    if creator.fcm_token:
        await fcm.send_push_notification(
            fcm_token=creator.fcm_token,
            title="Event partecipaton update",
            body=f"{user.username} will not be able to join your event",
            image_url=psql_event.cover_image_url,
        )
