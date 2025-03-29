import asyncio
from asyncio import AbstractEventLoop
from uuid import UUID

from kombu import Queue
from starlette import status

from app.api.exceptions.http_exc import DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_PSQL_DB_CONTEXT
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequest
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.elasticsearch.es_user_hiver import ESUserHiverBase
from app.database.models.psql.user import User
from app.database.models.psql.user_hiver import UserHiver
from app.depends.depends import get_es_query_service
from celery_app.celery_app import celery_app

celery_app.conf.task_queues = (Queue(name="partyup_user_hivers_queue"),)
celery_app.conf.task_routes = {
    "celery_respond_hiver_request": {
        "queue": "partyup_user_hivers_queue",
    },
}


@celery_app.task
def celery_respond_hiver_request(
    user: User,
    hiver_request_guid: UUID,
    accept: bool,
    user_hiver: UserHiver,
    psql_sender_guid: UUID,
    psql_hiver_request_status_value: str,
    psql_sender_fcm_token: str | None = None,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(future=get_es_query_service())
    es_hiver_request: ESHiverRequest | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            query=common_q.find_by_attr(guid=hiver_request_guid),
            model=ESHiverRequest,
            one=True,
        )
    )
    if not es_hiver_request:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find hiver request in ES DB linked to PSQL guid '{hiver_request_guid}'",
        )
    if accept:
        es_sender: ESUser | None = loop.run_until_complete(
            future=esclient.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(guid=psql_sender_guid),
                model=ESUser,
                one=True,
            )
        )
        es_receiver: ESUser | None = loop.run_until_complete(
            future=esclient.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(guid=user.guid),
                model=ESUser,
                one=True,
            )
        )
        if not es_sender or not es_receiver:
            raise DBException(
                api_context=DB_API_CONTEXT,
                db_context=DB_PSQL_DB_CONTEXT,
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Could not find hiver request in ES DB linked to PSQL guid '{psql_sender_guid}'",
            )
        es_sender.hivers_count += 1
        es_receiver.hivers_count += 1
        loop.run_until_complete(
            future=esclient.update(
                index=settings.ES_USERS_INDEX,
                doc_id=es_sender.id,
                **es_sender.model_dump(),
            )
        )
        loop.run_until_complete(
            future=esclient.update(
                index=settings.ES_USERS_INDEX,
                doc_id=es_receiver.id,
                **es_receiver.model_dump(),
            )
        )
        loop.run_until_complete(
            future=esclient.add(
                index=settings.ES_USER_HIVERS_INDEX,
                instance=ESUserHiverBase(**user_hiver.model_dump()),
            )
        )
    # update ES docs
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            doc_id=es_hiver_request.id,
            status=psql_hiver_request_status_value,
        )
    )
    if psql_sender_fcm_token:
        loop.run_until_complete(
            future=fcm.send_push_notification(
                fcm_token=psql_sender_fcm_token,
                title="Hiver request update",
                body=f"Your hiver request to {user.username} has been {psql_hiver_request_status_value.lower()}",
            )
        )
