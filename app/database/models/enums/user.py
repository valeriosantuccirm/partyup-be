from enum import Enum


class UserInfoStatus(Enum):
    """Status of required user info."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
