from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
)

from app.database.models.enums.hiver import HiverRequestStatus


class ESHiverRequestBase(BaseModel):
    """
    Represents the base structure for a Hiver request.

    This model stores the details of a request between a sender and a receiver,
    including the status and relevant timestamps.

    Attributes:
        created_at (datetime): The timestamp when the request was created.
        guid (UUID): A unique identifier for the request.
        receiver_guid (UUID): The unique identifier of the receiver.
        sender_guid (UUID): The unique identifier of the sender.
        status (HiverRequestStatus): The current status of the request (e.g., "PENDING").
    """

    created_at: datetime = Field(default=...)
    guid: UUID = Field(default=...)
    receiver_guid: UUID = Field(default=...)
    sender_guid: UUID = Field(default=...)
    status: HiverRequestStatus = Field(default=...)

    @field_serializer("created_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("guid", "sender_guid", "receiver_guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)

    @field_serializer("status")
    def strenum(self, enum: HiverRequestStatus) -> str:
        return enum.value


class ESHiverRequest(ESHiverRequestBase):
    """
    Represents a specific Hiver request with an identifier.

    Inherits from `ESHiverRequestBase` and adds a unique identifier for the request.

    Attributes:
        id (UUID): A unique identifier for the Hiver request.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
