from fastapi import Depends

from app.config import settings
from app.core import fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequestBase
from app.pubsub.public_users.schemas import HiverRequestSendBaseMsgData
from jobs.utils import elastic, extract_model_data


async def run_send_hiver_request(
    msg_data: str,
    elastic: ElasticsearchClient = Depends(elastic),
) -> None:
    model: HiverRequestSendBaseMsgData = extract_model_data(
        msg_data=msg_data,
        model=HiverRequestSendBaseMsgData,
    )
    await elastic.add(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        instance=ESHiverRequestBase(**model.hiver_request.model_dump()),
    )
    if model.receiver_fcm_token:
        await fcm.send_push_notification(
            fcm_token=model.receiver_fcm_token,
            title="You have a new hiver request",
            body=f"{model.user_username} want joining your hive",
            image_url=model.user_profile_img,
        )
