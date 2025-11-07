from typing import Any
from uuid import UUID

from pubsub.utils import _BasePubSubMsg  # pyright: ignore[reportPrivateUsage]
from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    field_serializer,
)

from app.database.models.psql.hiver_request import HiverRequest
from app.database.models.psql.user_follower import UserFollower


class UserCreatePubSubMsg(_BasePubSubMsg):
    instance: BaseModel = Field(default=...)

    @field_serializer("instance")
    def _dump(
        self,
        model: BaseModel,
    ) -> dict[str, Any]:
        return model.model_dump()


class UserUpdatePubSubMsg(UserCreatePubSubMsg): ...


class FollowUserBaseMsgData(BaseModel):
    user_follower: UserFollower = Field(default=...)
    psql_followed_user_guid: UUID = Field(default=...)
    user_guid: UUID = Field(default=...)
    user_username: StrictStr | None = Field(default=None)
    user_profile_img: StrictStr | None = Field(default=None)
    psql_followed_user_fcm_token: str | None = Field(default=None)

    @field_serializer("user_follower")
    def _dump(
        self,
        model: UserFollower,
    ) -> dict[str, Any]:
        return model.model_dump()


class UnfollowUserBaseMsgbData(BaseModel):
    psql_user_follower_guid: UUID = Field(default=...)
    psql_followed_user_guid: UUID = Field(default=...)
    user_guid: UUID = Field(default=...)


class HiverRequestSendBaseMsgData(BaseModel):
    hiver_request: HiverRequest = Field(default=...)
    user_username: StrictStr | None = Field(default=None)
    user_profile_img: StrictStr | None = Field(default=None)
    receiver_fcm_token: StrictStr | None = Field(default=None)

    @field_serializer("hiver_request")
    def _dump(
        self,
        model: HiverRequest,
    ) -> dict[str, Any]:
        return model.model_dump()


# final msg models
class FollowUserPubSubMsg(_BasePubSubMsg):
    data: FollowUserBaseMsgData = Field(default=...)


class UnfollowUserPubSubMsg(_BasePubSubMsg):
    data: UnfollowUserBaseMsgbData = Field(default=...)


class HiverRequestSendPubSubMsg(_BasePubSubMsg):
    data: HiverRequestSendBaseMsgData = Field(default=...)
