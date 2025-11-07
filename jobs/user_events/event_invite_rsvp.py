from fastapi import Depends
from sqlalchemy import Column

from app.config import settings
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from app.database.models.psql.user import User
from app.pubsub.events.schemas import EventRSVPPubSubBaseData
from jobs.utils import elastic, extract_model_data, psql


async def crun_rsvp_event_participation(
    msg_data: str,
    elastic: ElasticsearchClient = Depends(elastic),
    psql: PSQLClient = Depends(psql),
) -> None:
    model: EventRSVPPubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=EventRSVPPubSubBaseData,
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
        creator: User | None = await psql.find_one_or_none(
            model=User,
            criteria=(Column("guid") == model.psql_event_creator_guid,),
        )
        if creator and creator.fcm_token:
            await fcm.send_push_notification(
                fcm_token=creator.fcm_token,
                title="RSVP update",
                body=f"{model.user_username} just {model.psql_event_attendee_status.value.lower()} the invitation to your event",
            )
