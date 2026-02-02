from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictInt,
    StrictStr,
    field_serializer,
)

from core.database.models.psql.event_attendee import EventAttendee
from core.pubsub.utils import _BasePubSubMsg  # pyright: ignore[reportPrivateUsage]


class PublicEventJoinPubSubBaseData(BaseModel):
    event_attendee: EventAttendee = Field(default=...)
    psql_event_total_attendees_count: StrictInt = Field(default=...)
    psql_event_followers_attendees_count: StrictInt = Field(default=...)
    event_guid: UUID = Field(default=...)
    user_username: StrictStr | None = Field(default=None)
    psql_event_cover_image_url: StrictStr | None = Field(default=None)
    creator_fcm_token: StrictStr | None = Field(default=None)

    @field_serializer("event_attendee")
    def _dump(
        self,
        model: BaseModel,
    ) -> dict[str, Any]:
        return model.model_dump()


class PublicEventRevokePubSubMsgBaseData(BaseModel):
    user_guid: UUID = Field(default=...)
    psql_event_followers_attendees_count: StrictInt = Field(default=...)
    psql_event_total_attendees_count: StrictInt = Field(default=...)
    psql_event_attendee_guid: UUID = Field(default=...)
    event_guid: UUID = Field(default=...)
    psql_event_cover_image_url: StrictStr | None = Field(default=None)
    user_username: StrictStr | None = Field(default=None)
    creator_fcm_token: StrictStr | None = Field(default=None)


# final msd models
class PublicEventJoinPubSubMsg(_BasePubSubMsg):
    data: PublicEventJoinPubSubBaseData = Field(default=...)


class PublicEventRevokePubSubMsg(_BasePubSubMsg):
    data: PublicEventRevokePubSubMsgBaseData = Field(default=...)
