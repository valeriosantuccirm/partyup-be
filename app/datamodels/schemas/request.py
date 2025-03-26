from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import UploadFile
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)
from starlette import status
from starlette.datastructures import UploadFile as starletteUploadFile

from app.api.exceptions.http_exc import APIException
from app.constants import USER_API_CONTEXT
from app.datamodels.utils import validate_fileimage_extension


class UserCreateBase(BaseModel):
    """
    Model for creating a user.

    Attributes:
        :email (EmailStr): The user's email address.
        :hashed_psw (StrictStr): The user's hashed password.
        :username (StrictStr): The user's chosen username.
    """

    email: EmailStr = Field(default=...)
    hashed_psw: StrictStr = Field(default=..., alias="password")
    username: StrictStr = Field(default=...)


class UserRequestBaseModel(BaseModel):
    """
    Model representing the request base body for the user endpoint.

    Attributes:
        :bio (StrictStr): The user's bio.
        :date_of_birth (StrictStr): The user's date of birth in the format "DD/MM/YYYY".
        :first_name (StrictStr): The user's first name.
        :last_name (StrictStr): The user's last name.
        :location (StrictStr): The user's location (latitude, longitude).
        :location_name (StrictStr): The user's location name.
        :username (StrictStr | None): The username of the user.
    """

    bio: StrictStr = Field(default=...)
    date_of_birth: StrictStr = Field(default=...)
    first_name: StrictStr = Field(default=...)
    last_name: StrictStr = Field(default=...)
    location: StrictStr = Field(default="41.809380938573355, 12.679239750924646")
    location_name: StrictStr = Field(default=...)
    username: StrictStr | None = Field(default=None)

    @field_validator("date_of_birth", mode="before")
    def validate_date_of_birth(cls, value: str) -> str:
        """
        Validate the date of birth format

        Args:
            :value (str): The date of birth to validate.

        Raises:
            APIException: Raised when the date of birth does not meet the required format.

        Returns:
            :str: The validated date of birth.
        """
        try:
            datetime.strptime(value, "%d/%m/%Y")
        except ValueError:
            raise APIException(
                api_context=USER_API_CONTEXT,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date of birth must be in the format: DD/MM/YYYY and respect valid calendar dates",
            )
        return value


class UserRequestModel(UserRequestBaseModel):
    """
    Model representing the request body for the user endpoint.

    Args:

        :email (EmailStr): The user's email address.
    """

    email: EmailStr = Field(default=...)

    class Config:
        from_attributes = True
        populate_by_name = True


class EventCreateRequest(BaseModel):
    """
    Model representing the request body for creating an event.

    Attributes:
        :currency (StrictStr): The currency used for donations. Defaults to "€".
        :description (StrictStr | None): The event description.
        :end_date (datetime | None): The end date of the event.
        :location (StrictStr): The event location.
        :max_attendees (StrictInt): The maximum number of attendees for the event.
        :min_donation (StrictFloat): The minimum donation for the event.
        :start_date (datetime): The start date of the event.
        :title (StrictStr): The title of the event.
    """

    currency: StrictStr = Field(default="€")
    description: StrictStr | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    location: StrictStr = Field(default=...)
    max_attendees: StrictInt = Field(default=...)
    min_donation: StrictFloat = Field(default=0.0)
    start_date: datetime = Field(default=...)
    title: StrictStr = Field(default=...)

    @field_validator("min_donation")
    def validate_float(cls, value: StrictFloat) -> StrictFloat:
        if not round(number=float(value) * 100) == value * 100:
            raise APIException(
                api_context=USER_API_CONTEXT,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Value must have two decimal places only",
            )
        return value

    @classmethod
    def examples(cls) -> List[Dict[str, Any]]:
        return [
            {
                "currency": "€",
                "description": "Description",
                "end_date": datetime.now() + timedelta(days=8),
                "location": "41.809380938573355, 12.679239750924646",
                "start_date": datetime.now() + timedelta(days=7),
                "max_attendees": 10,
                "min_donation": 2.5,
                "title": "Title",
            },
            {
                "currency": "€",
                "description": "Description",
                "end_date": None,
                "location": "41.809380938573355, 12.679239750924646",
                "start_date": datetime.now() + timedelta(days=7),
                "max_attendees": 0,
                "min_donation": 2.5,
                "title": "Title",
            },
        ]


class EventCreateExtendedRequest(EventCreateRequest):
    """
    Extended version of the event creation request, adding support for cover image.

    Attributes:
        :cover_image (UploadFile | None): The cover image for the event.
    """

    cover_image: UploadFile | None = Field(default=None)

    @field_validator("cover_image")
    def validate_extension(
        cls, value: starletteUploadFile | None
    ) -> starletteUploadFile | None:
        return validate_fileimage_extension(value=value)


class UserEventUpdateRequest(BaseModel):
    """
    Model representing the request body for updating an event.

    Attributes:
        :description (StrictStr | None): The event description.
        :end_date (datetime | None): The end date of the event.
        :location_lat (StrictFloat): The latitude of the event location.
        :location_lon (StrictFloat): The longitude of the event location.
        :start_date (datetime): The start date of the event.
    """

    description: StrictStr | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    location_lat: StrictFloat = Field(default=...)
    location_lon: StrictFloat = Field(default=...)
    start_date: datetime = Field(default=...)

    @classmethod
    def examples(cls) -> List[Dict[str, Any]]:
        return [
            {
                "description": "Description",
                "end_date": datetime.now() + timedelta(days=8),
                "location": "41.809380938573355, 12.679239750924646",
                "start_date": datetime.now() + timedelta(days=7),
            },
            {
                "description": "Description",
                "end_date": None,
                "location": "41.809380938573355, 12.679239750924646",
                "start_date": datetime.now() + timedelta(days=7),
            },
        ]


class UserEventUpdateExtendedRequest(UserEventUpdateRequest):
    """
    Extended version of the user event update request, adding support for cover image.

    Attributes:
        :cover_image (UploadFile | None): The cover image for the event.
    """

    cover_image: UploadFile | None = Field(default=None)

    @field_validator("cover_image")
    def validate_extension(
        cls, value: starletteUploadFile | None
    ) -> starletteUploadFile | None:
        return validate_fileimage_extension(value=value)
