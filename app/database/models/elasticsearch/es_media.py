from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictStr,
    field_serializer,
)

from app.database.models.enums.media import MediaType


class ESMediaBase(BaseModel):
    """
    Represents the base structure for media content.

    This model stores details about media files associated with events, including
    metadata such as upload timestamps, file type, and ownership.

    Attributes:
        created_at (datetime): The timestamp when the media was created.
        event_guid (UUID): The unique identifier of the event associated with the media.
        file_url (StrictStr): The URL of the stored media file.
        guid (UUID): A unique identifier for the media entry.
        media_type (MediaType): The type of media (e.g., image, video).
        updated_at (datetime): The timestamp when the media was last updated.
        user_guid (UUID): The unique identifier of the user who uploaded the media.
    """

    created_at: datetime = Field(default=...)
    event_guid: UUID = Field(default=...)
    file_url: StrictStr = Field(default=...)
    media_type: MediaType = Field(default=...)
    guid: UUID = Field(default=...)
    updated_at: datetime = Field(default=...)
    user_guid: UUID = Field(default=...)

    @field_serializer("created_at", "updated_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("guid", "event_guid", "user_guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)

    @field_serializer("media_type")
    def strenum(self, enum: MediaType) -> str:
        return enum.value


class ESMedia(ESMediaBase):
    """
    Represents a specific Media with an identifier.

    Inherits from `ESMediaBase` and adds a unique identifier for the media.

    Attributes:
        id (UUID): A unique identifier for the Media.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
