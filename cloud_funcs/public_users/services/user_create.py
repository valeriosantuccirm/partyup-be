from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.models.elasticsearch.es_user import ESUser, ESUserBase
from core.logger import logger


async def run_create_user(
    msg_data: dict[str, Any],
) -> None:
    try:
        user: ESUserBase = extract_model_data(
            msg_data=msg_data,
            model=ESUserBase,
        )
        async with AsyncElasticsearch(
            hosts=[settings.ES_URI],
        ) as session:
            elastic: ElasticsearchClient = ElasticsearchClient(
                session=session,
            )
            logger.info("Init elastic client success")
            existing_user: ESUser | None = await elastic.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(
                    email=user.email,
                ),
                model=ESUser,
                one=True,
            )
            logger.info("Queried Elasticsearch to find existing user")
            if existing_user:
                logger.info(f"Existing user found {existing_user}. Exiting")
                raise Exception
            await elastic.add(
                index=settings.ES_USERS_INDEX,
                instance=user,
            )
            logger.info("Created new Elasticsearch user")
    except Exception as e:
        logger.error(e.args)
