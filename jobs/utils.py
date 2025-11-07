import base64
import json
from typing import Any, Literal

from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_user import ESUserBase
from app.database.session import esclient, psqlclient
from app.pubsub.events.schemas import (
    EventCancelPubSubBaseData,
    EventInvitePubSubBaseData,
    EventRSVPPubSubBaseData,
)
from app.pubsub.hivers.schemas import HiverReqRespPubSubBaseData
from app.pubsub.public_events.schemas import (
    PublicEventJoinPubSubBaseData,
    PublicEventRevokePubSubMsgBaseData,
)
from app.pubsub.public_users.schemas import (
    FollowUserBaseMsgData,
    HiverRequestSendBaseMsgData,
    UnfollowUserBaseMsgbData,
)


def extract_model_data[
    T: (
        ESUserBase,
        FollowUserBaseMsgData,
        UnfollowUserBaseMsgbData,
        HiverRequestSendBaseMsgData,
        PublicEventJoinPubSubBaseData,
        PublicEventRevokePubSubMsgBaseData,
        HiverReqRespPubSubBaseData,
        EventCancelPubSubBaseData,
        EventInvitePubSubBaseData,
        EventRSVPPubSubBaseData,
    )
](
    msg_data: str,
    model: type[T],
) -> T:
    data_str: str = base64.b64decode(msg_data).decode("utf-8")
    data_dict: dict[Literal["data"], Any] = json.loads(data_str)
    model_data: dict[str, Any] = data_dict["data"]
    return model(**model_data)


async def elastic() -> ElasticsearchClient:
    return await anext(esclient())

async def psql() -> PSQLClient:
    return await anext(psqlclient())
