from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
)


class ESUserFollowerBase(BaseModel):
    """
    Represents the base structure for a user follower relationship.

    This model stores the details of a follower relationship between two users.

    Attributes:
        created_at (datetime): The timestamp when the follower relationship was created.
        follower_guid (UUID): The unique identifier of the follower.
        guid (UUID): A unique identifier for the follower relationship.
        user_guid (UUID): The unique identifier of the user being followed.
    """

    created_at: datetime = Field(default=...)
    follower_guid: UUID = Field(default=...)
    guid: UUID = Field(default=...)
    user_guid: UUID = Field(default=...)

    @field_serializer("created_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("guid", "user_guid", "follower_guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)


class ESUserFollower(ESUserFollowerBase):
    """
    Represents a specific user follower relationship with an identifier.

    Inherits from `ESUserFollowerBase` and adds a unique identifier for the user follower relationship.

    Attributes:
        id (UUID): A unique identifier for the user follower relationship.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
