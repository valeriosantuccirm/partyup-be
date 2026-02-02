from typing import Any

from elasticsearch import AsyncElasticsearch
from sqlalchemy import Column

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from core.database.models.psql.user import User
from core.database.session import async_session_factory
from core.pubsub.events.schemas import EventInvitePubSubBaseData


async def run_send_event_invitations_to_hivers(
    msg_data: dict[str, Any],
) -> None:
    model: EventInvitePubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=EventInvitePubSubBaseData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        for hiver_guid in model.hivers_guids:
            await elastic.add(
                index=settings.ES_EVENT_ATTENDEES_INDEX,
                instance=ESEventAttendee(
                    **model.event_attendee.model_dump(),
                ),
            )
            async with async_session_factory() as session:  # type: ignore
                psql = PSQLClient(
                    session=session,  # type: ignore
                )
                hiver: User | None = await psql.find_one_or_none(
                    model=User,
                    criteria=(Column("guid") == hiver_guid,),
                )
                if hiver and hiver.fcm_token:
                    skip = True  # TODO: release when online: cannot be tested withoud app developer program
                    if not skip:
                        await fcm.send_push_notification(
                            fcm_token=hiver.fcm_token,
                            title="Event invitation",
                            body=f"You have been invited to join {model.psql_event_title} by {model.user_username}",
                        )
