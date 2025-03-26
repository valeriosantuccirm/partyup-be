from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_serializer,
)

from app.database.models.enums.event import EventStatus


class ESNewEvent(BaseModel):
    """
    Model representing a new event.

    Attributes:
        :created_at (datetime): The timestamp when the event was created.
        :creator_guid (UUID): The ID of the user who created the event.
        :cover_image (StrictStr | None): The cover image URL of the event.
        :currency (StrictStr): The currency used for donations.
        :description (StrictStr | None): The description of the event.
        :end_time (datetime | None): The end time of the event.
        :guid (UUID): The unique identifier for the event.
        :location_lat (StrictFloat): Latitude of the event's location.
        :location_lon (StrictFloat): Longitude of the event's location.
        :max_attendees (StrictInt | None): The maximum number of attendees for the event.
        :min_donation (StrictFloat): The minimum donation required for the event.
        :start_time (datetime): The start time of the event.
        :status (EventStatus): The status of the event.
        :title (StrictStr): The title of the event.
        :total_donations (StrictFloat): The total donations received for the event.
        :updated_at (datetime): The timestamp when the event was last updated.

    """

    cover_image: StrictStr | None = Field(default=None)
    created_at: datetime = Field(default=...)
    creator_guid: UUID = Field(default=...)
    currency: StrictStr = Field(default="€")
    description: StrictStr | None = Field(default=None)
    end_time: datetime | None = Field(default=None)
    guid: UUID = Field(default=...)
    location_lat: StrictFloat = Field(default=...)
    location_lon: StrictFloat = Field(default=...)
    max_attendees: StrictInt | None = Field(default=None)
    min_donation: StrictFloat = Field(default=0.0)
    start_time: datetime = Field(default=...)
    status: EventStatus = Field(default=...)
    title: StrictStr = Field(default=...)
    total_donations: StrictFloat = Field(default=0.0)
    updated_at: datetime = Field(default=...)

    @field_serializer("end_time", "start_time", "created_at", "updated_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("creator_guid", "guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)

    @field_serializer("status")
    def strenum(self, enum: Enum) -> str:
        return enum.value
