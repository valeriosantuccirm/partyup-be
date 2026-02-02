from enum import Enum
from typing import Self


class EventStatus(Enum):
    """Status of an event."""

    CANCELLED = "CANCELLED"
    ONGOING = "ONGOING"
    OUTDATED = "OUTDATED"
    UPCOMING = "UPCOMING"


class AttendeeType(Enum):
    """Type of user attending the event."""

    FOLLOWER = "FOLLOWER"
    HIVER = "HIVER"
    PUBLIC = "PUBLIC"


class EventAttendeeStatus(Enum):
    """Status of event request sent to an user."""

    CONFIRMED = "CONFIRMED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"
    WITHDRAWN = "WITHDRAWN"

    @classmethod
    def rsvp(cls, accept: bool) -> Self:
        return cls("CONFIRMED") if accept else cls("DECLINED")
