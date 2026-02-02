from typing import Any

from elasticsearch import AsyncElasticsearch
from sqlalchemy import Column

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.elasticsearch.es_event import ESEvent
from core.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from core.database.models.psql.user import User
from core.database.session import async_session_factory
from core.pubsub.events.schemas import EventRSVPPubSubBaseData


async def crun_rsvp_event_participation(
    msg_data: dict[str, Any],
) -> None:
    model: EventRSVPPubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=EventRSVPPubSubBaseData,
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
            query=common_q.find_by_attr(guid=model.psql_event_guid),
            model=ESEventAttendee,
            one=True,
        )
        if es_event_attendee:
            await elastic.update(
                index=settings.ES_EVENT_ATTENDEES_INDEX,
                doc_id=es_event_attendee.id,
                status=model.psql_event_attendee_status,
            )
            async with async_session_factory() as session:  # type: ignore
                psql = PSQLClient(
                    session=session,  # type: ignore
                )
                creator: User | None = await psql.find_one_or_none(
                    model=User,
                    criteria=(Column("guid") == model.psql_event_creator_guid,),
                )
                if creator and creator.fcm_token:
                    skip = True  # TODO: release when online: cannot be tested withoud app developer program
                    if not skip:
                        await fcm.send_push_notification(
                            fcm_token=creator.fcm_token,
                            title="RSVP update",
                            body=f"{model.user_username} just {model.psql_event_attendee_status.value.lower()} the invitation to your event",
                        )
