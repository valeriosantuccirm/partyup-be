from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from pydantic import EmailStr, StrictBool, StrictFloat, StrictInt, StrictStr
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, SQLModel

from app.database.models.enums.common import OAuthProvider
from app.database.models.enums.user import UserInfoStatus


class User(SQLModel, table=True):
    """
    Model representing a user entity in the database.

    Attributes:
        :auth_provider (OAuthProvider): The authentication provider used by the user.
        :bio (StrictStr | None): The user bio. Defaults to None.
        :created_at (datetime): The timestamp when the user was created.
        :date_of_birth (StrictStr | None): The user's date of birth. Defaults to None.
        :email (EmailStr): The user's email address (unique).
        :email_verified (StrictBool): Whether the user verified the email or not. Defaults to False.
        :event_participation (StrictInt): The number of attended events by the user. Defaults to 0.
        :fcm_token (StrictStr | None): The Firebase Cloud Messaging user's token. Defaults to None.
        :firebase_uid (StrictStr): The user Firebase ID.
        :first_name (StrictStr | None): The user's first name. Defaults to None.
        :followers_count (StrictInt): The number of followers. Defaults to 0.
        :following_count  (StrictInt): The number of followed users. Defaults to 0.
        :full_name (StrictStr | None): The composed name of the user. Defaults to None.
        :guid (UUID): The unique identifier for the user (primary key).
        :hivers_count (StrictInt): The number of user's hivers. Defaults to 0.
        :is_active (StrictBool): Indicates whether the user's account is active.
        :last_name (StrictStr | None): The user's last name. Defaults to None.
        :location (StrictStr): The main location of the user. Defaults to "41.8933203, 12.4829321".
        :locatoin_name (StrictStr | None): The main approximate location of the user. Defaults to None.
        :logout_timestamp (datetime): The timestamp when the user last logged out.
        :popularity_score (StrictFloat): The computed score for user popularity. Defaults to 0.0.
        :posts_count (StrictInt): The number of user's posts. Defaults to 0.
        :profile_image (StrictStr | None): The profile image of the user. Defaults to None.
        :tags (List[str]): The list of used tags. Defaults to [].
        :updated_at (datetime): The timestamp when the user's information was last updated.
        :user_info_status (UserInfoStatus): The status of the user required info. Defaults to UserInfoStatus.INCOMPLETE.
            NOTE: a user info status is considered COMPLETE when the following conditions are satisfied:
                - "first_name" must be provided
                - "last_name" must be provided
                - "date_of_birth" in format DD/MM/YYYY
                - "email_verified" must be True
                - "username" must be provided
                - "locatoin_name" must be provided
        :username (StrictStr | None): The user's username. Defaults to None.
    """

    auth_provider: OAuthProvider = Field(default=OAuthProvider.EMAIL, nullable=False)
    bio: StrictStr | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    date_of_birth: StrictStr | None = Field(default=None, nullable=True)
    email: EmailStr = Field(default=..., nullable=False, unique=True)
    email_verified: StrictBool = Field(default=False, nullable=False)
    event_participation: StrictInt = Field(default=0, nullable=False)
    fcm_token: StrictStr | None = Field(default=None, nullable=True)
    firebase_uid: StrictStr = Field(default=..., nullable=False)
    first_name: StrictStr | None = Field(default=None, nullable=True)
    followers_count: StrictInt = Field(default=0, nullable=False)
    following_count: StrictInt = Field(default=0, nullable=False)
    full_name: StrictStr | None = Field(default=None, nullable=True)
    guid: UUID = Field(
        default_factory=uuid4, nullable=False, primary_key=True, unique=True, index=True
    )
    hivers_count: StrictInt = Field(default=0, nullable=False)
    is_active: StrictBool = Field(default=False, nullable=False)
    last_name: StrictStr | None = Field(default=None, nullable=True)
    location: StrictStr = Field(
        default="41.8933203, 12.4829321",
        sa_column=Geometry(geometry_type="POINT", srid=4326),
    )
    location_name: StrictStr | None = Field(default=None, nullable=True)
    logout_timestamp: datetime | None = Field(default=None, nullable=True)
    popularity_score: StrictFloat = Field(default=0.0, nullable=False)
    posts_count: StrictInt = Field(default=0, nullable=False)
    profile_image: StrictStr | None = Field(default=None)
    tags: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(ARRAY(item_type=String))
    )
    updated_at: datetime = Field(default_factory=datetime.now, nullable=False)
    user_info_status: UserInfoStatus = Field(
        default=UserInfoStatus.INCOMPLETE, nullable=False
    )
    username: StrictStr | None = Field(default=None, nullable=True, unique=True)

    # Relationships
    # events: List["Event"] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
