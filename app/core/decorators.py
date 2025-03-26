import json
import traceback
from functools import wraps
from typing import Any, Callable, List, Literal

from asyncpg.exceptions import UniqueViolationError
from fastapi import Request
from fastapi.exceptions import HTTPException
from redis.typing import ResponseT
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.api.exceptions.http_exc import APIException, AWSException, DBException
from app.config import redis
from app.configlog import logger
from app.database.models.psql.user import User
from app.datamodels.schemas.response import UserResponseModel

CONN = "session"
CONN_VARS: tuple[Literal["session"], Literal["_"]] = ("session", "_")


def manage_transaction(func: Callable) -> Any:
    """
    Decorator for managing database transactions in a function.

    This decorator ensures that the database transaction is properly managed by
    handling commit, rollback, and closing of the session. It also handles different
    types of exceptions and raises appropriate HTTP exceptions with relevant status codes.

    Args:
        func (Callable): The function to be decorated. The decorated function is expected
            to accept a database session as one of its arguments.

    Returns:
        Any: The result of the decorated function after committing the transaction.

    Raises:
        HTTPException: Raises an HTTP exception with a status code and detail message
            if any database-related or value errors occur.
        Exception: Raises a generic HTTPException with status code 500 for unexpected exceptions.

    Notes:
        - The session is automatically rolled back in case of an exception.
        - The function will be executed inside a database transaction using the `async with _session.begin()` context manager.
    """

    @wraps(wrapped=func)
    async def wrapper(*args, **kwargs) -> Any:
        _session: AsyncSession | None = None
        for conn_var in CONN_VARS:
            if conn_var in kwargs:
                _session = kwargs[conn_var]
                break
        _session = _session if _session and isinstance(_session, AsyncSession) else AsyncSession()
        try:
            async with _session.begin():
                rv: Any = await func(*args, **kwargs)
                await _session.flush()
                await _session.commit()
                return rv
        except (APIException, DBException, AWSException) as e:
            await _session.rollback()
            raise e
        except (ValueError, TypeError) as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.args,
            )
        except (IntegrityError, UniqueViolationError) as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=e.args,
            )
        except KeyError as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.args,
            )
        except HTTPException as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            raise e
        except Exception as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.args,
            )
        finally:
            await _session.close()

    return wrapper


def cache_result(key: str, ttl: int) -> Any:
    """
    Decorator function to cache the result of an asynchronous function.

    Args:
        :key (str): The base key under which to cache the result. This key will be combined with offset and limit.
        :ttl (int): The time-to-live (TTL) duration for the cached result, in seconds.

    Returns:
        :Callable: A decorator function.

    Raises:
        :HTTPException: If an HTTP exception occurs during function execution.
        :Exception: If an unexpected exception occurs during function execution.
    """

    def decorator(func: Callable) -> Any:
        @wraps(wrapped=func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                cache_key = key
                if kwargs.get("request"):
                    request: Request = kwargs["request"]
                    # extract offset and limit from query parameters
                    offset: str | int = request.query_params.get("offset", default=0)
                    limit: str | int = request.query_params.get("limit", default=100)
                    cache_key: str = f"{key}_offset_{offset}_limit_{limit}"

                # check if the result is cached
                cached: ResponseT = redis.get(name=cache_key)
                if cached is not None:
                    return json.loads(s=str(cached))
                # compute the result
                func_result: List[User] = await func(*args, **kwargs)

                # parsing sqlalchemy ORM instances to pydantic models
                models: List[UserResponseModel] = [UserResponseModel(**user.model_dump()) for user in func_result]
                # cache the result
                redis.setex(
                    name=cache_key,
                    time=ttl,
                    value=json.dumps([m.model_dump() for m in models]),
                )
                return models
            except HTTPException as e:
                raise e
            except Exception as e:
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

        return wrapper

    return decorator


def clean_session(func: Callable) -> Any:
    """
    Decorator for managing database pending transactions when DB errors occur
    during depends injection.

    Args:
        :func (Callable): The function to be decorated.

    Returns:
        :Any: The result of the decorated function.

    Raises:
        :HTTPException: HTTP exceptions with appropriate status codes and details.
        :Exception: Any other unexpected exception with status code 500.
    """

    @wraps(wrapped=func)
    async def wrapper(*args, **kwargs) -> Any:
        _session: AsyncSession = kwargs[CONN]
        try:
            async with _session.begin():
                rv: Any = await func(*args, **kwargs)
                return rv
        except (DBException, APIException) as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            await _session.close()
            raise e
        except Exception as e:
            logger.error(traceback.format_exc())
            await _session.rollback()
            await _session.close()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.args,
            )

    return wrapper
