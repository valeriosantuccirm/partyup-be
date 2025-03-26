from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class UserFollower(SQLModel, table=True):
    """
    Model representing a user's follower entity in the database.

    Attributes:
        :created_at (datetime): The timestamp when the user follower was created.
        :follower_guid (UUID): The id of the user follower.
        :guid (UUID): The unique identifier for the user (primary key).
        :user_guid (UUID): The id of the user who's been followed.
    """

    __tablename__: str = "user_follower"

    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    guid: UUID = Field(default_factory=uuid4, nullable=False, primary_key=True, unique=True, index=True)

    # FKs
    follower_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
    user_guid: UUID = Field(foreign_key="user.guid", nullable=False, index=True)
