from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.models.elasticsearch.es_user import ESUser
from core.database.models.elasticsearch.es_user_follower import (
    ESUserFollower,
    ESUserFollowerBase,
)
from core.pubsub.public_users.schemas import FollowUserBaseMsgData


async def run_follow_user(
    msg_data: dict[str, Any],
) -> None:
    try:
        model: FollowUserBaseMsgData = extract_model_data(
            msg_data=msg_data,
            model=FollowUserBaseMsgData,
        )
        async with AsyncElasticsearch(
            hosts=[settings.ES_URI],
        ) as session:
            elastic: ElasticsearchClient = ElasticsearchClient(
                session=session,
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

            # check if user_follower in ES exists already
            es_user_follower: ESUserFollower | None = await elastic.find(
                index=settings.ES_USER_FOLLOWERS_INDEX,
                query=common_q.find_by_attr(guid=model.user_guid),
                model=ESUserFollower,
                one=True,
            )
            if es_user_follower:
                raise Exception
            await elastic.add(
                index=settings.ES_USER_FOLLOWERS_INDEX,
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
                following_count=es_follower_user.following_count + 1,
            )
            # send user notification
            if model.psql_followed_user_fcm_token:
                skip = True  # TODO: release when online: cannot be tested withoud app developer program
                if not skip:
                    await fcm.send_push_notification(
                        fcm_token=model.psql_followed_user_fcm_token,
                        title="You have a new follower",
                        body=f"{model.user_username} just started to follow you",
                        image_url=model.user_profile_img,
                    )
    except Exception as e:
        print(e)
        raise e
