from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.models.elasticsearch.es_user import ESUser
from core.database.models.elasticsearch.es_user_follower import ESUserFollower
from core.pubsub.public_users.schemas import UnfollowUserBaseMsgbData


async def run_unfollow_user(
    msg_data: dict[str, Any],
) -> None:
    model: UnfollowUserBaseMsgbData = extract_model_data(
        msg_data=msg_data,
        model=UnfollowUserBaseMsgbData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        # process follow logic
        es_user_follower: ESUserFollower | None = await elastic.find(
            index=settings.ES_USER_FOLLOWERS_INDEX,
            query=common_q.find_by_attr(
                guid=model.psql_user_follower_guid,
            ),
            model=ESUserFollower,
            one=True,
        )
        if not es_user_follower:
            raise Exception

        es_followed_user: ESUser | None = await elastic.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(
                guid=model.psql_followed_user_guid,
            ),
            model=ESUser,
            one=True,
        )
        es_follower_user: ESUser | None = await elastic.find(
            index=settings.ES_USERS_INDEX,
            query=common_q.find_by_attr(
                guid=model.user_guid,
            ),
            model=ESUser,
            one=True,
        )
        if not es_followed_user or not es_follower_user:
            raise Exception

        await elastic.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_followed_user.id,
            followers_count=es_followed_user.followers_count - 1,
        )
        await elastic.update(
            index=settings.ES_USERS_INDEX,
            doc_id=es_follower_user.id,
            following_count=es_follower_user.followers_count - 1,
        )
        await elastic.delete(
            index=settings.ES_USER_FOLLOWERS_INDEX,
            doc_id=es_user_follower.id,
        )
