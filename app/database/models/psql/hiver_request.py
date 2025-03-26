from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from app.database.models.enums.hiver import HiverRequestStatus


class HiverRequest(SQLModel, table=True):
    """
    Model representing a hiver request.

    Attributes:
        :created_at (datetime): Timestamp of request creation.
        :guid (UUID): Unique identifier for the request.
        :receiver_guid (UUID): User receiving the hiver request.
        :sender_guid (UUID): User sending the hiver request.
        :status (HiverRequestStatus): Request status. Defaults to HiverRequestStatus.PENDING.
    """

    __tablename__: str = "hiver_request"

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    receiver_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
    sender_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
    status: HiverRequestStatus = Field(
        default=HiverRequestStatus.PENDING, nullable=False
    )
