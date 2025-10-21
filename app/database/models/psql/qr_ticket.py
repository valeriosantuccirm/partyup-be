from datetime import datetime
from uuid import UUID, uuid4

from pydantic import StrictStr
from sqlmodel import (
    Field,  # pyright: ignore[reportUnknownVariableType]
    SQLModel,
)


class QRTicket(SQLModel, table=True):
    """
    Model representing a QR code ticket.

    Attributes:

    """

    __tablename__: str = "qr_ticket"  # pyright: ignore[reportIncompatibleVariableOverride]

    attendee_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    event_guid: UUID = Field(foreign_key="event.guid", nullable=False, index=True)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    qr_data: StrictStr = Field(default=..., nullable=False)
    ticket_url: StrictStr = Field(default=..., nullable=False)
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
