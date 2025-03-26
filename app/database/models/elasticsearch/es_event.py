from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_serializer,
)

from app.database.models.enums.event import EventStatus


class ESEventBase(BaseModel):
    """
    Represents the base structure for an event in the system.

    This model is used to store the event details including information such as
    the event's title, description, dates, status, creator, donation amounts,
    and other related metadata.

    Attributes:
        cover_image_filename (Optional[str]): The filename of the cover image.
        cover_image_url (Optional[str]): The URL of the cover image.
        creator_guid (UUID): The GUID of the event creator.
        creator_popularity_score (float): A score representing the creator's popularity.
        currency (str): The currency used for donations (default is "€").
        description (Optional[str]): A brief description of the event.
        end_date (Optional[datetime]): The event's end date and time.
        followers_attendees_count (int): The number of attendees following the event.
        guid (UUID): A unique identifier for the event.
        hivers_count (int): The number of hivers related to the event.
        hivers_reserved_slots (int): The number of reserved slots for hivers.
        is_private (bool): Whether the event is private (default is False).
        location (str): The location where the event is held.
        max_attendees (Optional[int]): The maximum number of attendees for the event.
        min_donation (float): The minimum donation required to attend the event (default is 0.0).
        ponr (Optional[datetime]): The point of no return date for the event.
        public_attendees_count (int): The number of public attendees for the event.
        start_date (datetime): The event's start date and time.
        status (EventStatus): The current status of the event (e.g., "UPCOMING").
        tags (List[str]): A list of tags associated with the event.
        title (str): The title or name of the event.
        total_attendees_count (int): The total number of attendees for the event.
        total_donations (float): The total amount of donations for the event (default is 0.0).
        updated_at (datetime): The last time the event details were updated.
    """

    currency: StrictStr = Field(default="€")
    description: StrictStr | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    location: StrictStr = Field(default=...)
    max_attendees: StrictInt | None = Field(default=None)
    min_donation: StrictFloat = Field(default=0.0)
    start_date: datetime = Field(default=...)
    title: StrictStr = Field(default=...)
    cover_image_url: StrictStr | None = Field(default=None)
    cover_image_filename: StrictStr | None = Field(default=None)
    created_at: datetime = Field(default=...)
    guid: UUID = Field(default=...)
    status: EventStatus = Field(default=...)
    total_donations: StrictFloat = Field(default=0.0)
    updated_at: datetime = Field(default=...)
    creator_guid: UUID = Field(default=...)
    hivers_count: StrictInt = Field(default=...)
    hivers_reserved_slots: StrictInt = Field(default=...)
    followers_attendees_count: StrictInt = Field(default=...)
    is_private: StrictBool = Field(default=...)
    ponr: datetime | None = Field(default=...)
    public_attendees_count: StrictInt = Field(default=...)
    total_attendees_count: StrictInt = Field(default=...)
    creator_popularity_score: StrictFloat = Field(default=...)
    tags: List[StrictStr] = Field(default=[])

    @field_serializer("end_date", "start_date", "created_at", "updated_at", "ponr")
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


class ESEvent(ESEventBase):
    """
    Represents a specific event with an identifier in the system.

    Inherits from `ESEventBase` and adds a unique event identifier.

    Attributes:
        id (UUID): A unique identifier for the event.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
