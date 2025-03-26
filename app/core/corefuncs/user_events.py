from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_ES_DB_CONTEXT, USER_EVENT_API_CONTEXT
from app.core import common, fcm
from app.core.common import upload_content_to_s3
from app.core.corefuncs import user_hivers
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q, events_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_event import ESEvent, ESEventBase
from app.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from app.database.models.enums.event import (
    AttendeeType,
    EventAttendeeStatus,
    EventStatus,
)
from app.database.models.psql.event import Event
from app.database.models.psql.event_attendee import EventAttendee
from app.database.models.psql.user import User
from app.datamodels.schemas.request import (
    EventCreateExtendedRequest,
    UserEventUpdateExtendedRequest,
)
from app.datamodels.schemas.response import PaginatedListedUser


async def create_event(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_request: EventCreateExtendedRequest,
) -> Event:
    media_path: str | None = None
    media_filename: str | None = None
    if event_request.cover_image:
        ext: str = await common.get_file_extension(
            media_filename=event_request.cover_image.filename,
        )
        media_path, media_filename = await upload_content_to_s3(
            media_content=event_request.cover_image,
            dirpath="user-profiles",
            ext=ext,
        )
    new_event = Event(
        cover_image_url=media_path,
        cover_image_filename=media_filename,
        currency=event_request.currency,
        description=event_request.description,
        end_date=event_request.end_date,
        location=event_request.location,
        max_attendees=event_request.max_attendees,
        min_donation=event_request.min_donation,
        start_date=event_request.start_date,
        title=event_request.title,
        creator_guid=user.guid,
        creator_popularity_score=user.popularity_score,
    )
    await db_session.add(
        instance=new_event,
    )
    es_new_event = ESEventBase(**dict(new_event))
    await esclient.add(
        index=settings.ES_EVENTS_INDEX,
        instance=es_new_event,
    )
    return new_event


async def get_user_events(
    esclient: ElasticsearchClient,
    user: User,
    status: EventStatus | None = None,
) -> List[ESEvent]:
    q: Dict[str, Any] = events_q.find_user_events(
        creator_guid=user.guid,
        status=status,
    )
    return await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=q,
        model=ESEvent,
    )


async def cancel_user_event(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
) -> None:
    psql_event, es_event = await common.find_es_and_psql_user_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )
    psql_event.status = EventStatus.CANCELLED
    psql_event.updated_at = datetime.now()
    await db_session.update(
        instance=psql_event,
    )
    await esclient.update(
        index=settings.ES_EVENTS_INDEX,
        doc_id=es_event.id,
        status=EventStatus.CANCELLED.value,
        updated_at=psql_event.updated_at,
    )
    # TODO: add logic of refund people when event is cancelled


async def update_user_event(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
    event_request: UserEventUpdateExtendedRequest,
    replace_cover_image: bool,
) -> Event:
    psql_event, es_event = await common.find_es_and_psql_user_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )
    if psql_event.status not in (EventStatus.UPCOMING,):
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            api_context=USER_EVENT_API_CONTEXT,
            detail="Only an event with status 'UPCOMING' can be updated",
        )
    media_path: UploadFile | str | None = psql_event.cover_image_url
    media_filename: str | None = psql_event.cover_image_filename
    if replace_cover_image:
        media_path = event_request.cover_image
        if event_request.cover_image:
            ext: str = await common.get_file_extension(
                media_filename=event_request.cover_image.filename
            )
            media_path, media_filename = await common.upload_content_to_s3(
                media_content=event_request.cover_image,
                dirpath="event-media",
                ext=ext,
            )
            if psql_event.cover_image_filename:
                await common.delete_content_from_s3(
                    media_filename=psql_event.cover_image_filename,
                )
    psql_event.sqlmodel_update(
        obj={
            **event_request.model_dump(),
            "cover_image_url": media_path,
            "cover_image_filename": media_filename,
            "updated_at": datetime.now(),
        }
    )
    updated_es_fields: dict[str, Any] = {
        **es_event.model_dump(),
        **psql_event.model_dump(),
    }
    updated_es_event = ESEventBase(**updated_es_fields)
    await db_session.update(
        instance=psql_event,
    )
    await esclient.update(
        index=settings.ES_EVENTS_INDEX,
        doc_id=es_event.id,
        **updated_es_event.model_dump(),
    )
    # TODO: add logic to notify people to ask for refund if needed
    return psql_event


async def send_event_invitations_to_hivers(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
    hivers_guids: List[UUID],
) -> None:
    psql_event, _ = await common.find_es_and_psql_user_event(
        esclient=esclient,
        db_session=db_session,
        user=user,
        event_guid=event_guid,
    )
    if psql_event.status != EventStatus.UPCOMING:
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            api_context=USER_EVENT_API_CONTEXT,
            detail="Only for an event with status 'UPCOMING' invitations can be sent",
        )
    linked_hivers_guids: PaginatedListedUser = await user_hivers.get_user_linked_hivers(
        esclient=esclient,
        user=user,
        limit=10000,
        fields=["guid"],
    )
    if set(hivers_guids) - set(
        [user.guid for user in linked_hivers_guids.listed_users]
    ):
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            api_context=USER_EVENT_API_CONTEXT,
            detail="Only linked hivers can be invited to an event",
        )
    if len(hivers_guids) > psql_event.hivers_reserved_slots:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            api_context=USER_EVENT_API_CONTEXT,
            detail="Number of hivers exceeds the reserved slots for the event",
        )
    q: Dict[str, Any] = events_q.find_event_attendees(
        event_guid=event_guid,
        user_guids=hivers_guids,
    )
    es_event_attendees: List[ESEventAttendee] = await esclient.find(
        index=settings.ES_EVENT_ATTENDEES_INDEX,
        query=q,
        model=ESEventAttendee,
    )
    if len(es_event_attendees) != len(hivers_guids):
        raise DBException(
            status_code=status.HTTP_404_NOT_FOUND,
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            detail="Could not find all hivers in the event attendees list in ES",
        )
    es_event_attendee_guids: List[UUID] = [
        event_attendee.guid for event_attendee in es_event_attendees
    ]
    for hiver_guid in hivers_guids:
        if hiver_guid in es_event_attendee_guids:
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                api_context=USER_EVENT_API_CONTEXT,
                detail=f"Hiver with guid '{hiver_guid}' has already been invited to the event",
            )
        new_event_attendee = EventAttendee(
            attendee_type=AttendeeType.HIVER,
            invitation_sent_at=datetime.now(),
            status=EventAttendeeStatus.PENDING,
            event_guid=event_guid,
            user_guid=hiver_guid,
        )
        await db_session.add(
            instance=new_event_attendee,
        )
        await esclient.add(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            instance=ESEventAttendee(**dict(new_event_attendee)),
        )
        hiver: User | None = await db_session.find_one_or_none(
            model=User,
            criteria=(Column("guid") == hiver_guid,),
        )
        if hiver and hiver.fcm_token:
            await fcm.send_push_notification(
                fcm_token=hiver.fcm_token,
                title="Event invitation",
                body=f"You have been invited to join {psql_event.title} by {user.username}",
            )


async def rsvp_event_participation(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    event_guid: UUID,
    accept: bool,
) -> None:
    psql_event: Event | None = await db_session.find_one_or_none(
        model=Event,
        criteria=(Column("guid") == event_guid,),
    )
    if not psql_event:
        raise DBException(
            status_code=status.HTTP_404_NOT_FOUND,
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            detail=f"Could not find event in PSQL DB with guid '{event_guid}'",
        )
    if psql_event.status != EventStatus.UPCOMING:
        raise APIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            api_context=USER_EVENT_API_CONTEXT,
            detail="Only for an event with status 'UPCOMING' RSVP can be sent",
        )
    es_event: ESEvent | None = await esclient.find(
        index=settings.ES_EVENTS_INDEX,
        query=common_q.find_by_attr(guid=event_guid),
        model=ESEvent,
        one=True,
    )
    if not es_event:
        raise DBException(
            status_code=status.HTTP_404_NOT_FOUND,
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            detail=f"Could not find event in ES DB with guid '{event_guid}'",
        )

    psql_event_attendee: EventAttendee | None = await db_session.find_one_or_none(
        model=EventAttendee,
        criteria=(
            Column("event_guid") == event_guid,
            Column("user_guid") == user.guid,
        ),
    )
    if not psql_event_attendee:
        raise APIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            api_context=USER_EVENT_API_CONTEXT,
            detail="User not invited",
        )
    if psql_event_attendee.status in (
        EventAttendeeStatus.CONFIRMED,
        EventAttendeeStatus.DECLINED,
    ):
        raise DBException(
            status_code=status.HTTP_400_BAD_REQUEST,
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            detail="User already RSVP'd to the event",
        )
    psql_event_attendee.status = EventAttendeeStatus.rsvp(accept=accept)
    es_event_attendee: ESEventAttendee | None = await esclient.find(
        index=settings.ES_EVENT_ATTENDEES_INDEX,
        query=common_q.find_by_attr(guid=psql_event.guid),
        model=ESEventAttendee,
        one=True,
    )
    if es_event_attendee:
        await esclient.update(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            doc_id=es_event_attendee.id,
            status=psql_event_attendee.status,
        )
    creator: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == psql_event.creator_guid,),
    )
    if creator and creator.fcm_token:
        await fcm.send_push_notification(
            fcm_token=creator.fcm_token,
            title="RSVP update",
            body=f"{user.username} just {psql_event_attendee.status.value.lower()} the invitation to your event",
        )
