from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.crud.elasticsearch.queries import common_q
from core.database.models.elasticsearch.es_hiver_request import ESHiverRequest
from core.database.models.elasticsearch.es_user import ESUser
from core.database.models.elasticsearch.es_user_hiver import ESUserHiverBase
from core.pubsub.hivers.schemas import HiverReqRespPubSubBaseData


async def run_respond_hiver_request(
    msg_data: dict[str, Any],
) -> None:
    model: HiverReqRespPubSubBaseData = extract_model_data(
        msg_data=msg_data,
        model=HiverReqRespPubSubBaseData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        es_hiver_request: ESHiverRequest | None = await elastic.find(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            query=common_q.find_by_attr(guid=model.hiver_request_guid),
            model=ESHiverRequest,
            one=True,
        )
        if not es_hiver_request:
            raise Exception
        if model.accept and model.user_hiver:
            es_sender: ESUser | None = await elastic.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(guid=model.psql_sender_guid),
                model=ESUser,
                one=True,
            )
            es_receiver: ESUser | None = await elastic.find(
                index=settings.ES_USERS_INDEX,
                query=common_q.find_by_attr(guid=model.user.guid),
                model=ESUser,
                one=True,
            )
            if not es_sender or not es_receiver:
                raise Exception

            es_sender.hivers_count += 1
            es_receiver.hivers_count += 1
            await elastic.update(
                index=settings.ES_USERS_INDEX,
                doc_id=es_sender.id,
                **es_sender.model_dump(),
            )
            await elastic.update(
                index=settings.ES_USERS_INDEX,
                doc_id=es_receiver.id,
                **es_receiver.model_dump(),
            )
            await elastic.add(
                index=settings.ES_USER_HIVERS_INDEX,
                instance=ESUserHiverBase(**model.user_hiver.model_dump()),
            )
        # update ES docs
        await elastic.update(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            doc_id=es_hiver_request.id,
            status=model.psql_hiver_request_status.value,
        )
        if model.psql_sender_fcm_token:
            skip = True  # TODO: release when online: cannot be tested withoud app developer program
            if not skip:
                await fcm.send_push_notification(
                    fcm_token=model.psql_sender_fcm_token,
                    title="Hiver request update",
                    body=f"Your hiver request to {model.user.username} has been {model.psql_hiver_request_status.value.lower()}",
                )
