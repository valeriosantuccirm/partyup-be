from datetime import datetime
from uuid import UUID, uuid4

from pydantic import StrictStr
from sqlmodel import Field, SQLModel

from app.database.models.enums.media import MediaType


class Media(SQLModel, table=True):
    """
    Model representing a media.

    Attributes:
        :created_at (datetime): Timestamp of media creation.
        :content_filename (StrictStr): The name of the content upload on AWS.
        :event_guid (UUID): The id of the event.
        :file_url (StrictStr): The meda file URL.
        :media_type (MediaType): The type of the media.
        :guid (UUID): The unique identifier for the media (primary key).
        :updated_at (datetime): Timestamp of media update.
        :user_guid (UUID): The id of the user who uploaded the event media.
    """

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    content_filename: StrictStr = Field(default=..., nullable=False)
    event_guid: UUID = Field(foreign_key="event.guid", nullable=False, index=True)
    file_url: StrictStr = Field(default=..., nullable=False)
    media_type: MediaType = Field(default=..., nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    user_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
