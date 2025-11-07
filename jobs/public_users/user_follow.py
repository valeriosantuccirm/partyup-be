from fastapi import Depends

from app.config import settings
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.elasticsearch.es_user_follower import ESUserFollowerBase
from app.pubsub.public_users.schemas import FollowUserBaseMsgData
from jobs.utils import elastic, extract_model_data


async def run_follow_user(
    msg_data: str,
    elastic: ElasticsearchClient = Depends(elastic),
) -> None:
    model: FollowUserBaseMsgData = extract_model_data(
        msg_data=msg_data,
        model=FollowUserBaseMsgData,
    )
    # process follow logic
    es_followed_user: ESUser | None = await elastic.find(
        index=settings.ES_USERS_INDEX,
        query=common_q.find_by_attr(guid=model.psql_followed_user_guid),
        model=ESUser,
        one=True,
    )
    es_follower_user: ESUser | None = await elastic.find(
        index=settings.ES_USERS_INDEX,
        query=common_q.find_by_attr(guid=model.user_guid),
        model=ESUser,
        one=True,
    )
    if not es_followed_user or not es_follower_user:
        raise Exception
    await elastic.add(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        instance=ESUserFollowerBase(
            **model.user_follower.model_dump(),
        ),
    )
    await elastic.update(
        index=settings.ES_USERS_INDEX,
        doc_id=es_followed_user.id,
        followers_count=es_followed_user.followers_count + 1,
    )
    await elastic.update(
        index=settings.ES_USERS_INDEX,
        doc_id=es_follower_user.id,
        followers_count=es_follower_user.followers_count + 1,
    )
    # send user notification
    if model.psql_followed_user_fcm_token:
        await fcm.send_push_notification(
            fcm_token=model.psql_followed_user_fcm_token,
            title="You have a new follower",
            body=f"{model.user_username} just started to follow you",
            image_url=model.user_profile_img,
        )
