import asyncio
from asyncio import AbstractEventLoop
from typing import Any, Dict
from uuid import UUID

from kombu import Queue
from starlette import status

from app.api.exceptions.http_exc import DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_ES_DB_CONTEXT
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.elasticsearch.es_event_attendee import (
    ESEventAttendee,
    ESEventAttendeeBase,
)
from app.depends.depends import get_es_query_service
from celery_app.celery_app import celery_app

celery_app.conf.task_queues = (Queue(name="partyup_events_queue"),)
celery_app.conf.task_routes = {
    "celery_join_public_event": {
        "queue": "partyup_events_queue",
    },
    "celery_revoke_join_event": {
        "queue": "partyup_events_queue",
    },
}


@celery_app.task
def celery_join_public_event(
    event_attendee_dict: Dict[str, Any],
    psql_event_total_attendees_count: int,
    psql_event_followers_attendees_count: int,
    event_guid: UUID,
    user_username: str,
    psql_event_cover_image_url: str,
    creator_fcm_token: str | None = None,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(
        future=get_es_query_service()
    )
    es_event: ESEvent | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_EVENTS_INDEX,
            query=common_q.find_by_attr(guid=event_guid),
            model=ESEvent,
            one=True,
        )
    )
    if not es_event:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with guid '{event_guid}' not found in ES",
        )
    loop.run_until_complete(
        future=esclient.add(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            instance=ESEventAttendeeBase(**event_attendee_dict),
        )
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=es_event.id,
            total_attendees_count=psql_event_total_attendees_count,
            followers_attendees_count=psql_event_followers_attendees_count,
        )
    )
    if creator_fcm_token:
        loop.run_until_complete(
            future=fcm.send_push_notification(
                fcm_token=creator_fcm_token,
                title="New event joiner!",
                body=f"{user_username} will join your event",
                image_url=psql_event_cover_image_url,
            )
        )


@celery_app.task
def celery_revoke_join_event(
    user_guid: UUID,
    psql_event_followers_attendees_count: int,
    psql_event_total_attendees_count: int,
    psql_event_attendee_guid: UUID,
    event_guid: UUID,
    psql_event_cover_image_url: str,
    user_username: str,
    creator_fcm_token: str | None = None,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(
        future=get_es_query_service()
    )
    es_event: ESEvent | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_EVENTS_INDEX,
            query=common_q.find_by_attr(guid=event_guid),
            model=ESEvent,
            one=True,
        )
    )
    if not es_event:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with guid '{event_guid}' not found in ES",
        )
    es_event_attendee: ESEventAttendee | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            query=common_q.find_by_attr(guid=psql_event_attendee_guid),
            model=ESEventAttendee,
            one=True,
        )
    )
    if not es_event_attendee:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with guid '{user_guid}' not found in event with guid '{event_guid}' in ES",
        )
    loop.run_until_complete(
        future=esclient.delete(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            doc_id=es_event_attendee.id,
        )
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=es_event.id,
            total_attendees_count=psql_event_total_attendees_count,
            followers_attendees_count=psql_event_followers_attendees_count,
        )
    )
    if creator_fcm_token:
        loop.run_until_complete(
            future=fcm.send_push_notification(
                fcm_token=creator_fcm_token,
                title="Event partecipaton update",
                body=f"{user_username} will not be able to join your event",
                image_url=psql_event_cover_image_url,
            )
        )
