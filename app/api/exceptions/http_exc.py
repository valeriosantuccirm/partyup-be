from typing import Any, Dict, Literal

from fastapi import HTTPException
from starlette import status


class APIException(HTTPException):
    """
    Custom exception class for API-related errors.

    Args:
        api_context (Literal["user", "user-event", "auth", "pub-event", "user-follower", "user-hiver"]):
            The context in which the exception occurred, e.g., "user", "auth", etc.
        status_code (int, optional): The HTTP status code for the exception response. Defaults to 500.
        detail (str, optional): A detailed message describing the error. Defaults to "Something went wrong".
        headers (Dict[str, Any], optional): Additional headers to include in the response. Defaults to an empty dictionary.

    Attributes:
        api_context (str): The context of the exception (e.g., "user", "auth").
        status_code (int): The HTTP status code associated with the exception.
        detail (str): The detailed message for the exception.
        headers (Dict[str, Any]): The headers to be included in the exception response.
    """

    def __init__(
        self,
        api_context: Literal["user", "user-event", "auth", "pub-event", "user-follower", "user-hiver"],
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Something went wrong",
        headers: Dict[str, Any] = {},
    ) -> None:
        self.api_context: str = api_context
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={
                **headers,
                "API-context": self.api_context,
            },
        )


class DBException(HTTPException):
    """
    Custom exception class for database-related errors.

    Args:
        api_context (Literal["database"], optional): The context in which the exception occurred, set to "database" by default.
        db_context (Literal["PSQL", "ES"], optional): The specific database context, e.g., "PSQL" for PostgreSQL or "ES" for Elasticsearch. Defaults to "PSQL".
        status_code (int, optional): The HTTP status code for the exception response. Defaults to 500.
        detail (str, optional): A detailed message describing the error. Defaults to "Database operation failed".
        headers (Dict[str, Any], optional): Additional headers to include in the response. Defaults to an empty dictionary.

    Attributes:
        api_context (str): The general context of the exception, always "database".
        db_context (str): The specific database context, e.g., "PSQL" or "ES".
        status_code (int): The HTTP status code associated with the exception.
        detail (str): The detailed message for the exception.
        headers (Dict[str, Any]): The headers to be included in the exception response.
    """

    def __init__(
        self,
        api_context: Literal["database"] = "database",
        db_context: Literal["PSQL", "ES"] = "PSQL",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "Database operation failed",
    ) -> None:
        self.api_context: str = api_context
        self.db_context: str = db_context
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={
                "API-context": self.api_context,
                "DB-context": self.db_context,
            },
        )


class AWSException(HTTPException):
    """
    Custom exception class for AWS-related errors during file upload or operations.

    Args:
        api_context (Literal["aws-upload"], optional): The context in which the exception occurred, set to "aws-upload" by default.
        status_code (int, optional): The HTTP status code for the exception response. Defaults to 500.
        detail (str, optional): A detailed message describing the error. Defaults to "AWS operation failed".
        headers (Dict[str, Any], optional): Additional headers to include in the response. Defaults to an empty dictionary.

    Attributes:
        api_context (str): The context of the exception, always "aws-upload".
        status_code (int): The HTTP status code associated with the exception.
        detail (str): The detailed message for the exception.
        headers (Dict[str, Any]): The headers to be included in the exception response.
    """

    def __init__(
        self,
        api_context: Literal["aws-upload"] = "aws-upload",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "AWS operation failed",
    ) -> None:
        self.api_context: str = api_context
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={
                "API-context": self.api_context,
            },
        )
