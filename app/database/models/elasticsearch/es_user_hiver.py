from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
)


class ESUserHiverRelations(BaseModel):
    """
    Represents the base structure for a user hiver PSQL base relationships.


    Attributes:
        guid (UUID): A unique identifier for the hiver relationship.
        user_guid (UUID): The unique identifier of the user in the hiver relationship.
    """

    hiver_guid: UUID = Field(default=...)
    user_guid: UUID = Field(default=...)


class ESUserHiverBase(ESUserHiverRelations):
    """
    Represents the base structure for a user hiver relationship.

    This model stores the details of a hiver relationship between two users.

    Attributes:
        created_at (datetime): The timestamp when the hiver relationship was created.
        guid (UUID): A unique identifier for the hiver relationship.
    """

    created_at: datetime = Field(default=...)
    guid: UUID = Field(default=...)

    @field_serializer("created_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("guid", "user_guid", "hiver_guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)


class ESUserHiver(ESUserHiverBase):
    """
    Represents a specific user hiver relationship with an identifier.

    Inherits from `ESUserHiverBase` and adds a unique identifier for the user hiver relationship.

    Attributes:
        id (UUID): A unique identifier for the user hiver relationship.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
