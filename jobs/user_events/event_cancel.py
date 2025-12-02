from typing import Any

from elasticsearch import AsyncElasticsearch

from app.config import settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.models.enums.event import EventStatus
from app.pubsub.events.schemas import EventCancelPubSubBaseData
from jobs.utils import extract_model_data


async def run_cancel_user_event(
    msg_data: dict[str, Any],
) -> None:
    model: EventCancelPubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=EventCancelPubSubBaseData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        await elastic.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=model.es_event_id,
            status=EventStatus.CANCELLED.value,
            updated_at=model.psql_event_updated_at,
        )
        # TODO: add logic of refund people when event is cancelled
