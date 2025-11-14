from typing import Any

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
    msg_data: dict[str, Any],
    model: type[T],
) -> T:
    return model(**msg_data)


async def elastic() -> ElasticsearchClient:
    return await anext(esclient())


async def psql() -> PSQLClient:
    return await anext(psqlclient())
