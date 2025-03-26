from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserHiver(SQLModel, table=True):
    """
    Model representing a user's hiver entity in the database.

    Attributes:
        :created_at (datetime): The timestamp when the user hiver was created.
        :guid (UUID): The unique identifier for the user (primary key).
        :hiver_guid (UUID):  The id of the user who's been added as hiver.
        :user_guid (UUID): The id of the user linked to the user hiver.
    """

    __tablename__: str = "user_hiver"

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, unique=True, index=True)

    # FKs
    hiver_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
    user_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
