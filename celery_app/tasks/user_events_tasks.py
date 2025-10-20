import asyncio
from asyncio import AbstractEventLoop
from datetime import datetime
from typing import Any
from uuid import UUID

from kombu import Queue
from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_ES_DB_CONTEXT
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from app.database.models.enums.event import EventStatus
from app.database.models.psql.user import User
from app.database.session import psql_session_manager_sync
from app.depends.depends import get_es_query_service
from celery_app.celery_app import celery_app

celery_app.conf.task_queues = (Queue(name="partyup_user_events_queue"),)
celery_app.conf.task_routes = {
    "celery_cancel_user_event": {
        "queue": "partyup_user_events_queue",
    },
}


@celery_app.task
def celery_cancel_user_event(
    es_event_id: UUID,
    psql_event_updated_at: datetime,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(
        future=get_es_query_service()
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=es_event_id,
            status=EventStatus.CANCELLED.value,
            updated_at=psql_event_updated_at,
        )
    )
    # TODO: add logic of refund people when event is cancelled


@celery_app.task
def celery_send_event_invitations_to_hivers(
    new_event_attendee_dict: dict[str, Any],
    hivers_guids: list[UUID],
    psql_event_title: str,
    user_username: str,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(
        future=get_es_query_service()
    )
    db_session: PSQLSessionManager | None = psql_session_manager_sync()
    if db_session:
        for hiver_guid in hivers_guids:
            loop.run_until_complete(
                future=esclient.add(
                    index=settings.ES_EVENT_ATTENDEES_INDEX,
                    instance=ESEventAttendee(**new_event_attendee_dict),
                )
            )
            hiver: User | None = loop.run_until_complete(
                future=db_session.find_one_or_none(
                    model=User,
                    criteria=(Column("guid") == hiver_guid,),
                )
            )
            if hiver and hiver.fcm_token:
                loop.run_until_complete(
                    future=fcm.send_push_notification(
                        fcm_token=hiver.fcm_token,
                        title="Event invitation",
                        body=f"You have been invited to join {psql_event_title} by {user_username}",
                    )
                )


@celery_app.task
def celery_rsvp_event_participation(
    event_guid: UUID,
    psql_event_guid: UUID,
    psql_event_attendee_status: str,
    psql_event_creator_guid: UUID,
    user_username: str,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(
        future=get_es_query_service()
    )
    db_session: PSQLSessionManager | None = psql_session_manager_sync()
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
            status_code=status.HTTP_404_NOT_FOUND,
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            detail=f"Could not find event in ES DB with guid '{event_guid}'",
        )

    es_event_attendee: ESEventAttendee | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            query=common_q.find_by_attr(guid=psql_event_guid),
            model=ESEventAttendee,
            one=True,
        )
    )
    if es_event_attendee:
        loop.run_until_complete(
            esclient.update(
                index=settings.ES_EVENT_ATTENDEES_INDEX,
                doc_id=es_event_attendee.id,
                status=psql_event_attendee_status,
            )
        )
    if db_session:
        creator: User | None = loop.run_until_complete(
            future=db_session.find_one_or_none(
                model=User,
                criteria=(Column("guid") == psql_event_creator_guid,),
            )
        )
        if creator and creator.fcm_token:
            loop.run_until_complete(
                future=fcm.send_push_notification(
                    fcm_token=creator.fcm_token,
                    title="RSVP update",
                    body=f"{user_username} just {psql_event_attendee_status.lower()} the invitation to your event",
                )
            )
