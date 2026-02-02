from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    field_serializer,
)

from core.database.models.enums.event import EventAttendeeStatus
from core.database.models.psql.event_attendee import EventAttendee
from core.pubsub.utils import _BasePubSubMsg  # pyright: ignore[reportPrivateUsage]


class EventCancelPubSubBaseData(BaseModel):
    es_event_id: UUID = Field(default=...)
    psql_event_updated_at: datetime = Field(default=...)


class EventRSVPPubSubBaseData(BaseModel):
    event_guid: UUID = Field(default=...)
    psql_event_guid: UUID = Field(default=...)
    psql_event_attendee_status: EventAttendeeStatus = Field(default=...)
    psql_event_creator_guid: UUID = Field(default=...)
    user_username: StrictStr | None = Field(default=...)


class EventInvitePubSubBaseData(BaseModel):
    event_attendee: EventAttendee = Field(default=...)
    hivers_guids: list[UUID] = Field(default=...)
    psql_event_title: StrictStr = Field(default=...)
    user_username: StrictStr | None = Field(default=None)

    @field_serializer("event_attendee")
    def _dump(
        self,
        model: BaseModel,
    ) -> dict[str, Any]:
        return model.model_dump()


# final msd models
class EventCancelPubSubPubSubMsg(_BasePubSubMsg):
    data: EventCancelPubSubBaseData = Field(default=...)


class EventRSVPPubSubPubSubMsg(_BasePubSubMsg):
    data: EventRSVPPubSubBaseData = Field(default=...)


class EventInvitePubSubPubSubMsg(_BasePubSubMsg):
    data: EventInvitePubSubBaseData = Field(default=...)
