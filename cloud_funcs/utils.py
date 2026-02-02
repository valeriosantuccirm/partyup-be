from typing import Any

from core.database.models.elasticsearch.es_user import ESUserBase
from core.pubsub.events.schemas import (
    EventCancelPubSubBaseData,
    EventInvitePubSubBaseData,
    EventRSVPPubSubBaseData,
)
from core.pubsub.hivers.schemas import HiverReqRespPubSubBaseData
from core.pubsub.public_events.schemas import (
    PublicEventJoinPubSubBaseData,
    PublicEventRevokePubSubMsgBaseData,
)
from core.pubsub.public_users.schemas import (
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
