import asyncio
from asyncio import AbstractEventLoop
from datetime import datetime
from uuid import UUID

from kombu import Queue

from app.config import settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.models.enums.event import EventStatus
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
    esclient: ElasticsearchClient = loop.run_until_complete(future=get_es_query_service())
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=es_event_id,
            status=EventStatus.CANCELLED.value,
            updated_at=psql_event_updated_at,
        )
    )
    # TODO: add logic of refund people when event is cancelled
