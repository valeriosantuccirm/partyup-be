from typing import Any

from elasticsearch import AsyncElasticsearch

from cloud_funcs.utils import extract_model_data
from core import fcm
from core.config import settings
from core.database.crud.elasticsearch.esclient import ElasticsearchClient
from core.database.models.elasticsearch.es_hiver_request import ESHiverRequestBase
from core.pubsub.public_users.schemas import HiverRequestSendBaseMsgData


async def run_send_hiver_request(
    msg_data: dict[str, Any],
) -> None:
    model: HiverRequestSendBaseMsgData = extract_model_data(
        msg_data=msg_data,
        model=HiverRequestSendBaseMsgData,
    )
    async with AsyncElasticsearch(
        hosts=[settings.ES_URI],
    ) as session:
        elastic: ElasticsearchClient = ElasticsearchClient(
            session=session,
        )
        await elastic.add(
            index=settings.ES_HIVER_REQUESTS_INDEX,
            instance=ESHiverRequestBase(**model.hiver_request.model_dump()),
        )
        if model.receiver_fcm_token:
            skip = True  # TODO: release when online: cannot be tested withoud app developer program
            if not skip:
                await fcm.send_push_notification(
                    fcm_token=model.receiver_fcm_token,
                    title="You have a new hiver request",
                    body=f"{model.user_username} want joining your hive",
                    image_url=model.user_profile_img,
                )
