from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
)

from app.database.models.enums.event import AttendeeType, EventAttendeeStatus


class ESEventAttendeeBase(BaseModel):
    attendee_type: AttendeeType = Field(default=...)
    created_at: datetime = Field(default=...)
    invitation_sent_at: datetime | None = Field(default=None)
    rsvp_date: datetime = Field(default=...)
    status: EventAttendeeStatus = Field(default=...)
    event_guid: UUID = Field(default=...)
    user_guid: UUID = Field(default=...)
    guid: UUID = Field(default=...)

    @field_serializer("rsvp_date", "created_at", "invitation_sent_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("event_guid", "user_guid", "guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)

    @field_serializer("status", "attendee_type")
    def strenum(self, enum: Enum) -> str:
        return enum.value


class ESEventAttendee(ESEventAttendeeBase):
    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
