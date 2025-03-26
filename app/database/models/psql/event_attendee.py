from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.database.models.enums.event import AttendeeType, EventAttendeeStatus


class EventAttendee(SQLModel, table=True):
    """
    Model representing an event attendee entity in the database.

    Attributes:
        :attendee_type (AttendeeType): The type of attendee.
        :created_at (datetime): The timestamp when the event attendee was created.
        :event_guid (UUID): The id of the event.
        :guid (UUID): A unique identifier for the event attendee.
        :invitation_sent_at (datetime | None): The date when the invitation was sent. Defaults to None.
        :rsvp_date (datetime): The date when the attendee confirmed to join.
        :status (EventAttendeeStatus): The status of the invitation.
        :user_guid (UUID): The id of the user attending the event.
    """

    __tablename__: str = "event_attendee"

    attendee_type: AttendeeType = Field(default=..., nullable=False)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    invitation_sent_at: datetime | None = Field(default=None, nullable=True)
    rsvp_date: datetime = Field(default_factory=datetime.now, nullable=False)
    status: EventAttendeeStatus = Field(default=..., nullable=False)
    # FKs
    event_guid: UUID = Field(foreign_key="event.guid", nullable=False, primary_key=True)
    user_guid: UUID = Field(foreign_key="user.guid", nullable=False, primary_key=True)
