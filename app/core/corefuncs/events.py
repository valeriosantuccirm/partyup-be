import json
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from fastapi import HTTPException, UploadFile
from sqlalchemy import Column
from starlette import status

from app.config import settings
from app.core import common
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import events_q
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_event import ESEvent
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
from app.database.models.psql.qr_ticket import QRTicket
from app.database.models.psql.user import User
from app.database.models.psql.user_follower import UserFollower
from app.datamodels.schemas.response import PaginatedEvents
from app.pubsub.public_events.enums import PublicEventsPubSubEvent
from app.pubsub.public_events.schemas import (
    PublicEventJoinPubSubBaseData,
    PublicEventJoinPubSubMsg,
    PublicEventRevokePubSubMsg,
    PublicEventRevokePubSubMsgBaseData,
)
from app.pubsub.publisher import Publisher
from jobs.payments.src.schema.qr_data import QRData


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
    q: dict[str, Any] = events_q.build_leaderboard_events(
        creator_guid=user.guid,
        status=status,
        user_bio=user.bio,
        user_lat=lat,
        user_lon=lon,
        radius=radius,
        limit=limit,
        offset=offset,
    )
    events: list[ESEvent] = await esclient.find(
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
    q: dict[str, Any] = events_q.search_events(
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
    events: list[ESEvent] = await esclient.find(
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
    db_session: PSQLClient,
    user: User,
    media_content: UploadFile,
    event_guid: UUID,
) -> Media:
    event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not event or event.status not in (
        EventStatus.ONGOING,
        EventStatus.OUTDATED,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
    return psql_media


async def join_public_event(
    db_session: PSQLClient,
    user: User,
    event_guid: UUID,
) -> None:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event or psql_event.status != EventStatus.UPCOMING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' not found in PSQL or status is not 'UPCOMING'",
        )
    if psql_event.total_attendees_count == psql_event.max_attendees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' has reached the maximum number of attendees",
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{psql_event.creator_guid}' not found",
        )
    publisher: Publisher = Publisher(
        topic_id=settings.GOOGLE_ELASTIC_EVENTS_TOPIC_ID,
    )
    await publisher.publish(
        data=PublicEventJoinPubSubMsg(
            event=PublicEventsPubSubEvent.event_join,
            data=PublicEventJoinPubSubBaseData(
                event_attendee=event_attendee,
                psql_event_total_attendees_count=psql_event.total_attendees_count,
                psql_event_followers_attendees_count=psql_event.followers_attendees_count,
                event_guid=event_guid,
                user_username=user.username,
                psql_event_cover_image_url=psql_event.cover_image_url,
                creator_fcm_token=creator.fcm_token,
            ),
        )
    )


async def revoke_join_event(
    db_session: PSQLClient,
    user: User,
    event_guid: UUID,
) -> None:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event or psql_event.status != EventStatus.UPCOMING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Event with guid '{event_guid}' not found in PSQL or status is not 'UPCOMING'",
        )
    psql_event_attendee: EventAttendee | None = await db_session.find_one_or_none(
        model=EventAttendee,
        criteria=(
            Column("event_guid") == event_guid,
            Column("user_guid") == user.guid,
        ),
    )
    if not psql_event_attendee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{user.guid}' not found in event with guid '{event_guid}' in PSQL",
        )
    psql_event.total_attendees_count -= 1
    creator: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == psql_event.creator_guid,),
    )
    if not creator:
        raise HTTPException(
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
    publisher: Publisher = Publisher(
        topic_id=settings.GOOGLE_ELASTIC_EVENTS_TOPIC_ID,
    )
    await publisher.publish(
        data=PublicEventRevokePubSubMsg(
            event=PublicEventsPubSubEvent.event_revoke,
            data=PublicEventRevokePubSubMsgBaseData(
                user_guid=user.guid,
                psql_event_followers_attendees_count=psql_event.followers_attendees_count,
                psql_event_total_attendees_count=psql_event.total_attendees_count,
                psql_event_attendee_guid=psql_event_attendee.guid,
                event_guid=event_guid,
                psql_event_cover_image_url=psql_event.cover_image_url,
                user_username=user.username,
                creator_fcm_token=creator.fcm_token,
            ),
        )
    )


async def aknowledge_data_by_scanned_qr_code(
    db_session: PSQLClient,
    token: str,
) -> dict[str, bool]:
    f = Fernet(settings.FERNET_KEY)

    plaintext_bytes: bytes = f.decrypt(token.encode("utf-8"))
    qrdata = QRData(**json.loads(plaintext_bytes.decode("utf-8")))

    qr_ticket: QRTicket | None = await db_session.find_one_or_none(
        model=QRTicket,
        criteria=(Column("attendee_guid") == qrdata.attendee.guid,),
    )

    if not qr_ticket:
        raise Exception

    if qr_ticket.expired:
        raise Exception

    if qr_ticket.acknowledged:
        return {
            "acknowledged": qr_ticket.acknowledged,
        }

    event_attendee: EventAttendee | None = await db_session.find_one_or_none(
        model=EventAttendee,
        criteria=(
            Column("event_guid") == qrdata.event.guid,
            Column("user_guid") == qrdata.attendee.guid,
        ),
    )

    if not event_attendee:
        raise Exception

    event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("creator_guid") == qrdata.creator.guid,),
    )

    if not event:
        raise Exception

    qr_ticket.acknowledged = True
    event.total_attendees_count += 1

    return {
        "acknowledged": qr_ticket.acknowledged,
    }
