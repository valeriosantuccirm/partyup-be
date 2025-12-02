from typing import Any

from elasticsearch import AsyncElasticsearch

from app.config import settings
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.elasticsearch.es_event_attendee import ESEventAttendeeBase
from app.pubsub.public_events.schemas import PublicEventJoinPubSubBaseData
from jobs.utils import extract_model_data


async def run_join_public_event(
    msg_data: dict[str, Any],
) -> None:
    model: PublicEventJoinPubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=PublicEventJoinPubSubBaseData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        es_event: ESEvent | None = await elastic.find(
            index=settings.ES_EVENTS_INDEX,
            query=common_q.find_by_attr(guid=model.event_guid),
            model=ESEvent,
            one=True,
        )
        if not es_event:
            raise Exception

        await elastic.add(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            instance=ESEventAttendeeBase(
                **model.event_attendee.model_dump(),
            ),
        )
        await elastic.update(
            index=settings.ES_EVENTS_INDEX,
            doc_id=es_event.id,
            total_attendees_count=model.psql_event_total_attendees_count,
            followers_attendees_count=model.psql_event_followers_attendees_count,
        )
        if model.creator_fcm_token:
            skip = True  # TODO: release when online: cannot be tested withoud app developer program
            if not skip:
                await fcm.send_push_notification(
                    fcm_token=model.creator_fcm_token,
                    title="New event joiner!",
                    body=f"{model.user_username} will join your event",
                    image_url=model.psql_event_cover_image_url,
                )
