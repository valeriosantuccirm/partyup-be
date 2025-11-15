from typing import Any

from elasticsearch import AsyncElasticsearch

from app.config import settings
from app.configlog import logger
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_user import ESUser, ESUserBase
from jobs.utils import extract_model_data


async def run_update_user(
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
            if not existing_user:
                logger.info("No existing user found to update. Exiting")
                raise Exception
            fields_to_update: dict[str, Any] = {
                **existing_user.model_dump(exclude={"id", "_id"}),
                **user.model_dump(),
            }
            await elastic.update(
                doc_id=existing_user.id,
                index=settings.ES_USERS_INDEX,
                **fields_to_update,
            )
            logger.info("Created new Elasticsearch user")
    except Exception as e:
        logger.error(e.args)
