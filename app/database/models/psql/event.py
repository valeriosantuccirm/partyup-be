from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from pydantic import StrictBool, StrictFloat, StrictInt, StrictStr
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, SQLModel

from app.database.models.enums.event import EventStatus


class Event(SQLModel, table=True):
    """
    Model representing an event in the database.

    Attributes:
        :creator_guid (UUID): The ID of the user who created the event (foreign key to the User table).
        :creator_popularity_score (StrictFloat): The popularity score of the user who creates the event. Defaults to 0.0.
        :cover_image_filename (StrictStr | None): The cover image file name. Defaults to None.
        :cover_image_url (StrictStr | None): The URL of the event's cover image (hosted on AWS S3). Defaults to None.
        :currency (StrictStr): The currency used for donations.
        :created_at (datetime): The timestamp when the event was created.
        :description (StrictStr | None): A brief description of the event. Defaults to None.
        :end_date (datetime | None): The end date of the event, if applicable. Defaults to None.
        :followers_attendees_count (StrictInt): The followers joining the event. Defaults to 0.
        :guid (UUID): A unique identifier for the event.
        :hivers_count (StrictInt): The number of user's hivers who join the event. Defaults to 0.
        :hivers_reserved_slots (StrictInt): The number of reserved slots for the user's hivers. Defaults to 0.
        :is_last_minute (StrictBool): Whether the event is a last minute event or not. Defaults to False.
        :is_private (StrictBool): Whether the event is public or not. Defaults to False.
        :location (StrictStr): The location of the event.
        :max_attendees (StrictInt | None): The maximum number of attendees for the event. Defaults to None.
        :min_donation (StrictFloat): The minimum donation required for the event. Defaults to 0.0.
        :ponr (datetime | None): The date after which it's no longer possible to ask for a refund. Defaults to None.
        :public_attendees_count (StrictInt): The number of public users who join the event. Defaults to 0.
        :start_date (datetime): The start date of the event.
        :status (EventStatus): The current status of the event. Defaults to UPCOMING.
        :tags (List[str]): The list of used tags. Defaults to [].
        :title (StrictStr): The title of the event.
        :total_attendees_count (StrictInt): The total number of attendees. Defaults to 0.
        :total_donations (StrictFloat): The total donations received for the event. Defaults to 0.0.
        :updated_at (datetime): The timestamp when the event was last updated.
    """

    creator_popularity_score: StrictFloat = Field(default=0.0)
    cover_image_filename: StrictStr | None = Field(default=None, nullable=True)
    cover_image_url: StrictStr | None = Field(default=None, nullable=True)  # AWS S3 URL
    currency: StrictStr = Field(default=..., nullable=False)  # TODO: map in enums
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    description: StrictStr | None = Field(default=None, nullable=True)
    end_date: datetime | None = Field(default=None, nullable=True)
    followers_attendees_count: StrictInt = Field(default=0, nullable=False)
    guid: UUID = Field(
        default_factory=uuid4, primary_key=True, unique=True, nullable=False
    )
    hivers_count: StrictInt = Field(default=0, nullable=False)
    hivers_reserved_slots: StrictInt = Field(default=0, nullable=False)
    is_last_minute: StrictBool = Field(default=False, nullable=False)
    is_private: StrictBool = Field(default=False, nullable=False)
    location: StrictStr = Field(
        default=..., sa_column=Geometry(geometry_type="POINT", srid=4326)
    )
    max_attendees: StrictInt = Field(default=0, nullable=False)
    min_donation: StrictFloat = Field(default=0.0, nullable=False)
    ponr: datetime | None = Field(default=None, nullable=True)
    public_attendees_count: StrictInt = Field(default=0, nullable=False)
    start_date: datetime = Field(default=..., nullable=False)
    status: EventStatus = Field(default=EventStatus.UPCOMING, nullable=False)
    tags: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(ARRAY(item_type=String))
    )
    title: StrictStr = Field(default=..., nullable=False)
    total_attendees_count: StrictInt = Field(default=0, nullable=False)
    total_donations: StrictFloat = Field(default=0.0, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)

    # FKs
    creator_guid: UUID = Field(foreign_key="user.guid", nullable=False)
    # Relationships
    # users: List["User"] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
