from typing import Any

from elasticsearch import AsyncElasticsearch
from sqlalchemy import Column

from app.config import settings
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_event_attendee import ESEventAttendee
from app.database.models.psql.user import User
from app.database.session import async_session_factory
from app.pubsub.events.schemas import EventInvitePubSubBaseData
from jobs.utils import extract_model_data


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
