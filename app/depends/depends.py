from typing import Annotated, Any, Dict, Tuple
from uuid import UUID

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from firebase_admin import auth
from firebase_admin._user_mgt import UserRecord
from redis.asyncio.client import PubSub
from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException
from app.config import redis
from app.constants import AUTH_API_CONTEXT, PUB_EVENT_API_CONTEXT, USER_API_CONTEXT
from app.core import common
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.enums.event import EventAttendeeStatus
from app.database.models.psql.event_attendee import EventAttendee
from app.database.models.psql.user import User
from app.database.redis import RedisClient, redis_client
from app.database.session import psql_session_manager
from app.datamodels.schemas.auth import FirebaseUser

security = HTTPBearer()


async def get_firebase_user(
    authcreds: Annotated[HTTPAuthorizationCredentials, Depends(dependency=security)],
) -> FirebaseUser:
    """
    Get the current user based on the provided authentication token.

    Args:
        :token (str): The authentication token obtained from the request headers.
        :session (AsyncSession, optional): The SQLAlchemy database session. Defaults to Depends(dependency=psql_session_manager).

    Returns:
        :User: The user corresponding to the provided authentication token.

    Raises:
        :HTTPException: An exception indicating authentication failure.
            This could occur due to invalid credentials or missing user data.
    """
    try:
        token: str = authcreds.credentials
        decoded_token: Dict[str, Any] = auth.verify_id_token(id_token=token)
        firebase_user: UserRecord = auth.get_user(uid=decoded_token["uid"])
        redis.set(
            name=f"access_token:{firebase_user.uid}",
            value=token,
            ex=600,
        )  # 10 mins
        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token["email"],
            email_verified=firebase_user.email_verified,
            access_token=token,
            providers=[p.provider_id for p in firebase_user.provider_data if p.provider_id is not None],
            profile_picture_url=firebase_user.photo_url,
            full_name=firebase_user.display_name,
        )
    except (auth.ExpiredIdTokenError, auth.InvalidIdTokenError) as e:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token. Details: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not validate credentials. Details: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db_session: PSQLSessionManager = Depends(dependency=psql_session_manager),
    firebase_user: FirebaseUser = Depends(dependency=get_firebase_user),
) -> User | None:
    psql_user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("firebase_uid") == firebase_user.uid,),
    )
    if not psql_user:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    psql_user.email_verified = firebase_user.email_verified
    return psql_user


async def admit_user(
    current_user: Annotated[User, Depends(dependency=get_current_user)],
) -> User:
    if not await common.are_user_info_complete(user=current_user):
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User must provide mandatory info before proceeding",
        )
    return current_user


async def get_attendee(
    event_guid: UUID,
    user: User = Depends(dependency=get_current_user),
    db_session: PSQLSessionManager = Depends(dependency=psql_session_manager),
) -> User:
    """Check if the user is an attendee of the event."""
    event_attendee: EventAttendee | None = await db_session.find_one_or_none(
        model=EventAttendee,
        criteria=(
            Column("event_guid") == event_guid,
            Column("user_guid") == user.guid,
        ),
    )
    if event_attendee and event_attendee.status != EventAttendeeStatus.CONFIRMED:
        raise APIException(
            api_context=PUB_EVENT_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not allowed to post media for this event because he's not a confirmed attendee",
        )
    return user


async def pubsub_event(
    event_guid: UUID,
    user: User = Depends(dependency=get_current_user),
) -> Tuple[RedisClient, PubSub]:
    redis_set_key: str = f"event_users:{event_guid}"
    if not redis_client.redis:
        await redis_client.connect()
    if not redis_client.redis.sismember(
        name=redis_set_key,
        value=str(user.guid),
    ):
        raise APIException(
            api_context=USER_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not allowed to access event media stream",
        )
    pubsub: PubSub = redis_client.redis.pubsub()
    await pubsub.subscribe(f"event_media:{event_guid}")
    return redis_client, pubsub


async def get_redis_client() -> RedisClient:
    if not redis_client.redis:
        await redis_client.connect()
    return redis_client


async def get_es_query_service() -> ElasticsearchClient:
    return ElasticsearchClient()
