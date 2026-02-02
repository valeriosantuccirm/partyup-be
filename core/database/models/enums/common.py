from enum import Enum


class OAuthProvider(Enum):
    """Provider used to authenticate."""

    EMAIL = "EMAIL"
    GOOGLE = "GOOGLE"
