from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_serializer,
)


class ESUserBase(BaseModel):
    """
    Represents the base structure for a user.

    This model stores the details of a user's profile information.

    Attributes:
        bio (StrictStr | None): A short biography of the user.
        created_at (datetime): The timestamp when the user's account was created.
        date_of_birth (StrictStr | None): The user's date of birth.
        firebase_uid (StrictStr): The unique identifier for the user from Firebase.
        first_name (StrictStr | None): The user's first name.
        followers_count (StrictInt): The number of users following the user.
        following_count (StrictInt): The number of users the user is following.
        full_name (StrictStr): The user's full name.
        guid (UUID): A unique identifier for the user.
        hivers_count (StrictInt): The number of hivers associated with the user.
        last_name (StrictStr | None): The user's last name.
        location (StrictStr | None): The user's location.
        location_name (StrictStr | None): The name of the user's location.
        popularity_score (StrictFloat): The user's popularity score.
        profile_image (StrictStr | None): The URL of the user's profile image.
        tags (List[StrictStr]): A list of tags associated with the user.
        total_posts (StrictInt): The total number of posts made by the user.
        updated_at (datetime): The timestamp when the user's profile was last updated.
        username (StrictStr | None): The user's username.
    """

    bio: StrictStr | None = Field(default=None)
    created_at: datetime = Field(default=...)
    date_of_birth: StrictStr | None = Field(default=None)
    firebase_uid: StrictStr = Field(default=...)
    first_name: StrictStr | None = Field(default=None)
    followers_count: StrictInt = Field(default=0)
    following_count: StrictInt = Field(default=0)
    full_name: StrictStr | None = Field(default=None)
    guid: UUID = Field(default=...)
    hivers_count: StrictInt = Field(default=0)
    last_name: StrictStr | None = Field(default=None)
    location: StrictStr | None = Field(default=None)
    location_name: StrictStr | None = Field(default=None)
    popularity_score: StrictFloat = Field(default=0.0)
    profile_image: StrictStr | None = Field(default=None)
    tags: List[StrictStr] = Field(default=[])
    total_posts: StrictInt = Field(default=0)
    updated_at: datetime = Field(default_factory=datetime.now)
    username: StrictStr | None = Field(default=None)

    @field_serializer("created_at", "updated_at")
    def strtoime(self, value: datetime | None) -> str | None:
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @field_serializer("guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)


class ESUser(ESUserBase):
    """
    Represents a user with an identifier.

    Inherits from `ESUserBase` and adds a unique identifier for the user.

    Attributes:
        id (UUID): A unique identifier for the user.
    """

    id: UUID = Field(default=...)

    @field_serializer("id")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)
