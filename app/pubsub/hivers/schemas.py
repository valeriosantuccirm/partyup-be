from typing import Any
from uuid import UUID

from pubsub.utils import _BasePubSubMsg  # pyright: ignore[reportPrivateUsage]
from pydantic import (
    BaseModel,
    Field,
    StrictBool,
    StrictStr,
    field_serializer,
)

from app.database.models.enums.hiver import HiverRequestStatus
from app.database.models.psql.user import User
from app.database.models.psql.user_hiver import UserHiver


class HiverReqRespPubSubBaseData(BaseModel):
    user: User = Field(default=...)
    hiver_request_guid: UUID = Field(default=...)
    accept: StrictBool = Field(default=...)
    user_hiver: UserHiver | None = Field(default=None)
    psql_sender_guid: UUID = Field(default=...)
    psql_hiver_request_status: HiverRequestStatus = Field(default=...)
    psql_sender_fcm_token: StrictStr | None = Field(default=...)

    @field_serializer("event_attendee", "user_hiver")
    def _dump(
        self,
        model: User | UserHiver | None,
    ) -> dict[str, Any] | None:
        if isinstance(model, (User, UserHiver)):
            return model.model_dump()
        return model


# final msd models
class HiverReqRespPubSubMsg(_BasePubSubMsg):
    data: HiverReqRespPubSubBaseData = Field(default=...)
