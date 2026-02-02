from enum import Enum


class HiverRequestStatus(Enum):
    """Status of a request to join the user's hive."""

    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    PENDING = "PENDING"
