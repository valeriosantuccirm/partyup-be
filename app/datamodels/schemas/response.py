from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_serializer,
    field_validator,
)

from app.database.models.elasticsearch.es_event import ESEvent
from app.database.models.enums.event import EventStatus
from app.database.models.enums.user import UserInfoStatus


class UserResponseModel(BaseModel):
    """
    Model representing the response model for a user.

    Attributes:
        :bio (StrictStr | None): The user's bio. Defaults to None.
        :date_of_birth (StrictStr | None): The user's date of birth. Defaults to None.
        :email (EmailStr): The user's email address.
        :email_verified (StrictBool): Indicates if the user's email is verified.
        :first_name (StrictStr | None): The user's first name. Defaults to None.
        :full_name (StrictStr | None): The complete name. Defaulrs to None.
        :guid (UUID): The unique identifier for the user.
        :is_active (StrictBool): Indicates if the user's account is active.
        :last_name (StrictStr | None): The user's last name. Defaults to None.
        :user_info_status (UserInfoStatus): The status of the user's information.
        :username (StrictStr | None): The user's username. Defaults to None.
    """

    bio: StrictStr | None = Field(default=None)
    date_of_birth: StrictStr | None = Field(default=None)
    email: EmailStr = Field(default=...)
    email_verified: StrictBool = Field(default=...)
    first_name: StrictStr | None = Field(default=None)
    full_name: StrictStr | None = Field(default=None)
    guid: UUID = Field(default=...)
    is_active: StrictBool = Field(default=...)
    last_name: StrictStr | None = Field(default=None)
    user_info_status: UserInfoStatus = Field(default=UserInfoStatus.INCOMPLETE)
    username: StrictStr | None = Field(default=None)

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

    @field_serializer("guid")
    def uuid_to_str(self, guid: UUID) -> str:
        return str(guid)


class ESUserEventResponse(BaseModel):
    """
    Model representing the response for an event associated with a user.

    Attributes:
        :cover_image_filename (StrictStr | None): The filename of the event's cover image. Defaults to None.
        :cover_image_url (StrictStr | None): The URL of the event's cover image. Defaults to None.
        :guid (UUID): The unique identifier for the event in PSQL.
        :id (UUID): The unique identifier for the event.
        :start_date (datetime): The start date of the event.
        :title (StrictStr): The title of the event.
    """

    cover_image_filename: StrictStr | None = Field(default=None)
    cover_image_url: StrictStr | None = Field(default=None)
    guid: UUID = Field(default=...)
    id: UUID = Field(default=...)
    start_date: datetime = Field(default=...)
    title: StrictStr = Field(default=...)


class ESUserEventDetailsResponse(ESUserEventResponse):
    """
    Model representing the detailed response for an event associated with a user.

    Attributes:
        :currency (StrictStr): The currency used for donations.
        :creator_popularity_score (StrictFloat): The popularity score of the event creator.
        :description (StrictStr): The event's description.
        :end_date (datetime | None): The end date of the event. Defaults to None.
        :location (StrictStr): The location of the event.
        :max_attendees (StrictInt | None): The maximum number of attendees for the event. Defaults to None.
        :min_donation (StrictFloat): The minimum donation for the event.
        :status (EventStatus): The status of the event.
        :total_donations (StrictFloat): The total donations for the event.
    """

    currency: StrictStr = Field(default=...)
    creator_popularity_score: StrictFloat = Field(default=0.0)
    description: StrictStr = Field(default=...)
    end_date: datetime | None = Field(default=None)
    location: StrictStr = Field(default=...)
    max_attendees: StrictInt | None = Field(default=None)
    min_donation: StrictFloat = Field(default=0.0)
    status: EventStatus = Field(default=...)
    total_donations: StrictFloat = Field(default=0.0)


class ESListedUser(BaseModel):
    """
    Model representing a listed user.

    Attributes:
        :followers_count (StrictInt): The number of followers the user has.
        :full_name (StrictStr): The user's full name.
        :guid (UUID): The unique identifier for the user.
        :hivers_count (StrictInt): The number of hivers the user has.
        :id (UUID): The unique identifier for the user.
        :profile_image (StrictStr | None): The URL of the user's profile image. Defaults to None.
        :username (StrictStr): The username of the user.
    """

    followers_count: StrictInt = Field(default=...)
    full_name: StrictStr = Field(default=...)
    guid: UUID = Field(default=...)
    hivers_count: StrictInt = Field(default=...)
    id: UUID = Field(default=...)
    profile_image: StrictStr | None = Field(default=None)
    username: StrictStr = Field(default=...)


class Paginated(BaseModel):
    """
    Model representing the pagination information.

    Attributes:
        :limit (StrictInt): The maximum number of results per page.
        :offset (StrictInt): The offset to start fetching results.
        :total_results (StrictInt): The total number of results available.
    """

    limit: StrictInt = Field(default=0)
    offset: StrictInt = Field(default=0)
    total_results: StrictInt = Field(default=0)


class PaginatedEvents(Paginated):
    """
    Model representing paginated events.

    Attributes:
        :events (List[ESEvent]): A list of events.
    """

    events: List[ESEvent] = Field(default=[])


class PaginatedListedUser(Paginated):
    """
    Model representing paginated listed users.

    Attributes:
        :listed_users (List[ESListedUser]): A list of listed users.
    """

    listed_users: List[ESListedUser] = Field(default=...)


class MapsLocation(BaseModel):
    """
    Model representing a location on a map.

    Attributes:
        :display_name (StrictStr): The name of the location to display.
        :lat (StrictFloat): The latitude of the location.
        :lon (StrictFloat): The longitude of the location.
    """

    display_name: StrictStr = Field(default=...)
    lat: StrictFloat = Field(default=...)
    lon: StrictFloat = Field(default=...)

    @field_validator("lat", "lon", mode="before")
    def cast_to_float(cls, value: str) -> float:
        return float(value)
