from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.models.elasticsearch.es_event import ESEvent
from core.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from core.pubsub.public_events.schemas import (
    PublicEventRevokePubSubMsgBaseData,
)


async def run_revoke_join_event(
    msg_data: dict[str, Any],
) -> None:
    model: PublicEventRevokePubSubMsgBaseData = extract_model_data(
        msg_data=msg_data,
        model=PublicEventRevokePubSubMsgBaseData,
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

        es_event_attendee: ESEventAttendee | None = await elastic.find(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            query=common_q.find_by_attr(guid=model.psql_event_attendee_guid),
            model=ESEventAttendee,
            one=True,
        )
        if not es_event_attendee:
            raise Exception

        await elastic.delete(
            index=settings.ES_EVENT_ATTENDEES_INDEX,
            doc_id=es_event_attendee.id,
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
                    title="Event partecipaton update",
                    body=f"{model.user_username} will not be able to join your event",
                    image_url=model.psql_event_cover_image_url,
                )
