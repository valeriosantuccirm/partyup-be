import asyncio
from asyncio import AbstractEventLoop
from typing import Any, Dict
from uuid import UUID

from kombu import Queue
from starlette import status

from app.api.exceptions.http_exc import DBException
from app.config import settings
from app.constants import DB_API_CONTEXT, DB_ES_DB_CONTEXT
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequestBase
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.elasticsearch.es_user_follower import ESUserFollower, ESUserFollowerBase
from app.depends.depends import get_es_query_service
from celery_app.celery_app import celery_app

celery_app.conf.task_queues = (Queue(name="partyup_public_users_queue"),)
celery_app.conf.task_routes = {
    "celery_follow_user": {
        "queue": "partyup_public_users_queue",
    },
}


@celery_app.task
def celery_follow_user(
    user_follower_dict: Dict[str, Any],
    psql_followed_user_guid: UUID,
    user_guid: UUID,
    user_username: str,
    user_profile_image: str,
    psql_followed_user_fcm_token: str | None = None,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(future=get_es_query_service())
    es_followed_user: ESUser | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=psql_followed_user_guid),
            model=ESUser,
            one=True,
        )
    )
    es_follower_user: ESUser | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=user_guid),
            model=ESUser,
            one=True,
        )
    )
    if not es_followed_user or not es_follower_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find users in ES DB with given criteria",
        )
    loop.run_until_complete(
        future=esclient.add(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            instance=ESUserFollowerBase(**user_follower_dict),
        )
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_followed_user.id,
            followers_count=es_followed_user.followers_count + 1,
        )
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_follower_user.id,
            followers_count=es_follower_user.followers_count + 1,
        )
    )
    if psql_followed_user_fcm_token:
        asyncio.run(
            main=fcm.send_push_notification(
                fcm_token=psql_followed_user_fcm_token,
                title="You have a new follower",
                body=f"{user_username} just started to follow you",
                image_url=user_profile_image,
            )
        )


@celery_app.task
async def celery_unfollow_user(
    psql_user_follower_guid: UUID,
    psql_followed_user_guid: UUID,
    user_guid: UUID,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(future=get_es_query_service())
    q: Dict[str, Any] = common_q.find_by_attr(guid=psql_user_follower_guid)
    es_user_follower: ESUserFollower | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_USER_FOLLOWERS_INDEX,
            query=q,
            model=ESUserFollower,
            one=True,
        )
    )
    if not es_user_follower:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user follower in ES DB with given criteria",
        )
    es_followed_user: ESUser | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=psql_followed_user_guid),
            model=ESUser,
            one=True,
        )
    )
    es_follower_user: ESUser | None = loop.run_until_complete(
        future=esclient.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(guid=user_guid),
            model=ESUser,
            one=True,
        )
    )
    if not es_followed_user or not es_follower_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find users in ES DB with given criteria",
        )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_followed_user.id,
            followers_count=es_followed_user.followers_count - 1,
        )
    )
    loop.run_until_complete(
        future=esclient.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_follower_user.id,
            followers_count=es_follower_user.followers_count - 1,
        )
    )
    loop.run_until_complete(
        future=esclient.delete(
            index=settings.ES_USER_FOLLOWERS_INDEX,
            doc_id=es_user_follower.id,
        )
    )


@celery_app.task
def celery_send_hiver_request(
    hiver_request_dict: Dict[str, Any],
    user_username: str,
    user_profile_image: str,
    receiver_fcm_token: str | None = None,
) -> None:
    loop: AbstractEventLoop = asyncio.get_event_loop()
    esclient: ElasticsearchClient = loop.run_until_complete(future=get_es_query_service())
    loop.run_until_complete(
        future=esclient.add(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            instance=ESHiverRequestBase(**hiver_request_dict),
        )
    )
    if receiver_fcm_token:
        loop.run_until_complete(
            future=fcm.send_push_notification(
                fcm_token=receiver_fcm_token,
                title="You have a new hiver request",
                body=f"{user_username} want joining your hive",
                image_url=user_profile_image,
            )
        )
