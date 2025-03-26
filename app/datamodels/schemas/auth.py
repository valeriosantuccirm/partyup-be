import re
from typing import List

from pydantic import BaseModel, EmailStr, Field, StrictBool, StrictStr, field_validator
from starlette import status

from app.api.exceptions.http_exc import APIException
from app.constants import USER_API_CONTEXT


class Token(BaseModel):
    """
    Model representing an authentication token with its type.

    Attributes:
        :access_token (StrictStr): The token string used for authentication.
        :token_type (StrictStr): The type of token. Defaults to "bearer".
    """

    access_token: StrictStr = Field(default=...)
    token_type: StrictStr = Field(default="bearer")


class FCMToken(BaseModel):
    """
    Model representing an FCM (Firebase Cloud Messaging) token.

    Attributes:
        :fcm_token (StrictStr): The Firebase Cloud Messaging token used for notifications.
    """

    fcm_token: StrictStr = Field(default=...)


class FirebaseUser(BaseModel):
    """
    Model representing a Firebase user.

    Attributes:
        :access_token (StrictStr): The Firebase access token.
        :email (EmailStr): The user's email address.
        :email_verified (StrictBool): Whether the user's email is verified.
        :full_name (StrictStr | None): The user's full name, if available.
        :profile_picture_url (StrictStr | None): The URL of the user's profile picture, if available.
        :providers (List[StrictStr]): A list of authentication providers used by the user (e.g., "google", "facebook").
        :uid (StrictStr): The unique Firebase user identifier.
    """

    access_token: StrictStr = Field(default=...)
    email: EmailStr = Field(default=...)
    email_verified: StrictBool = Field(default=...)
    full_name: StrictStr | None = Field(default=None)
    profile_picture_url: StrictStr | None = Field(default=None)
    providers: List[StrictStr] = Field(default=[])
    uid: StrictStr = Field(default=...)


class PasswordResetRequest(BaseModel):
    """
    Model representing a password reset request.

    Attributes:
        :password (StrictStr): The new password to be set.
    """

    password: StrictStr = Field(default=...)

    @field_validator("password", mode="before")
    def validate_psw(cls, value: str) -> str:
        """
        Validate the password format.

        Args:
            :value (str): The password to validate.

        Raises:
            :APIException: Raised when the password does not meet the required format.

        Returns:
            :str: The validated password.
        """
        if not re.match(
            pattern="^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
            string=value,
        ):
            raise APIException(
                api_context=USER_API_CONTEXT,
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be longer then 10 characters, contain at least one upper case letter and one special character",
            )
        return value
