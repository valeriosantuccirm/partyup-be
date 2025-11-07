from fastapi import Depends

from app.config import settings
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.models.elasticsearch.es_user import ESUser, ESUserBase
from jobs.utils import elastic, extract_model_data


async def run_create_user(
    msg_data: str,
    elastic: ElasticsearchClient = Depends(elastic),
) -> None:
    user: ESUserBase = extract_model_data(
        msg_data=msg_data,
        model=ESUserBase,
    )
    existing_user: ESUser | None = await elastic.find(
        index=settings.ES_USERS_INDEX,
        query=common_q.find_by_attr(
            username=user.username,
        ),
        model=ESUser,
        one=True,
    )
    if existing_user:
        raise Exception
    await elastic.add(
        index=settings.ES_USERS_INDEX,
        instance=user,
    )
