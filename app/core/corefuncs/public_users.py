from typing import Any, Dict, List, Set
from uuid import UUID

from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import settings
from app.constants import (
    DB_API_CONTEXT,
    DB_ES_DB_CONTEXT,
    DB_PSQL_DB_CONTEXT,
    USER_HIVER_API_CONTEXT,
)
from app.core import common, fcm
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import users_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequestBase
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.enums.hiver import HiverRequestStatus
from app.database.models.psql.hiver_request import HiverRequest
from app.database.models.psql.user import User
from app.database.models.psql.user_follower import UserFollower
from app.datamodels.schemas.response import ESListedUser, PaginatedListedUser
from celery_app.tasks.public_users_tasks import (
    celery_follow_user,
    celery_send_hiver_request,
    celery_unfollow_user,
)


async def search_accounts(
    esclient: ElasticsearchClient,
    user: User,
    lat: float | None,
    lon: float | None,
    radius: int,
    user_input: str,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedListedUser:
    # TODO: handle user location. Need to convert the string to lat/lon pairs
    if not lat or not lon:
        data: Dict[str, Any] | None = await common.search_map_location(
            query=user.location,
            limit=1,
            first=True,
        )
        if data:
            lat = float(data["lat"])
            lon = float(data["lon"])

    mqs: List[Dict[str, Any]] = users_q.find_linked_users_ids(
        left_index=settings.ES_USER_HIVERS_INDEX,
        right_index=settings.ES_USER_FOLLOWERS_INDEX,
        left_term={"hiver_guid": user.guid},
        right_term={"follower_guid": user.guid},
        left_source=[
            "user_guid",
        ],
        right_source=[
            "user_guid",
        ],
    )
    hiver_hits, follower_hits = await esclient.msearch(mquery=mqs)
    hiver_guids: Set[UUID] = {
        UUID(hex=hit["_source"]["user_guid"]) for hit in hiver_hits
    }
    follower_guids: Set[UUID] = {
        UUID(hex=hit["_source"]["user_guid"]) for hit in follower_hits
    }
    q: Dict[str, Any] = users_q.find_public_users(
        user_bio=user.bio,
        user_guid=str(user.guid),
        user_username=user.username,
        user_fullname=user.full_name,
        user_hiver_guids=list(hiver_guids),
        user_follower_guids=list(follower_guids),
        user_input=user_input,
        user_lat=lat,
        user_lon=lon,
        radius=radius,
        limit=limit,
        offset=offset,
        source=[
            "username",
            "profile_image",
            "followers_count",
            "guid",
            "_id",
            "hivers_count",
            "full_name",
        ],
    )
    ranked_accounts: List[ESListedUser] = await esclient.find(
        index=settings.ES_USERS_INDEX,
        query=q,
        model=ESListedUser,
    )
    return PaginatedListedUser(
        total_results=len(ranked_accounts),
        limit=limit,
        offset=offset,
        listed_users=ranked_accounts,
    )


async def follow_user(
    db_session: PSQLSessionManager,
    user: User,
    user_guid: UUID,
) -> None:
    user_follower: UserFollower | None = await db_session.find_one_or_none(
        model=UserFollower,
        criteria=(
            Column("follower_guid") == user.guid,
            Column("user_guid") == user_guid,
        ),
    )
    if user_follower:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_409_CONFLICT,
            detail="Follower relation already exists",
        )
    psql_followed_user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == user_guid,),
    )
    if not psql_followed_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user in PSQL DB with given criteria",
        )
    user_follower = UserFollower(
        user_guid=user_guid,
        follower_guid=user.guid,
    )
    await db_session.add(
        instance=user_follower,
    )
    user.following_count += 1
    psql_followed_user.followers_count += 1
    celery_follow_user.apply_async(
        args=(
            user_follower.model_dump(),
            psql_followed_user.guid,
            user_guid,
            user.username,
            user.profile_image,
            psql_followed_user.fcm_token,
        ),
        queue="partyup_public_users_queue",
        priority=1,
    )


async def unfollow_user(
    db_session: PSQLSessionManager,
    user: User,
    user_guid: UUID,
) -> None:
    psql_user_follower: UserFollower | None = await db_session.find_one_or_none(
        model=UserFollower,
        criteria=(
            Column("user_guid") == user_guid,
            Column("follower_guid") == user.guid,
        ),
    )
    if not psql_user_follower:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user follower in PSQL DB with given criteria",
        )
    psql_followed_user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == user_guid,),
    )
    if not psql_followed_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user in PSQL DB with given criteria",
        )
    psql_followed_user.followers_count -= 1
    user.following_count -= 1
    await db_session.delete(
        instance=psql_user_follower,
    )
    celery_unfollow_user.apply_async(
        args=(
            psql_user_follower.guid,
            psql_followed_user.guid,
            user.guid,
        ),
        queue="partyup_public_users_queue",
        priority=2,
    )


async def send_hiver_request(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    user_guid: UUID,
) -> HiverRequest:
    psql_user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == user_guid,),
    )
    if not psql_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_PSQL_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find user in PSQL DB with guid '{user_guid}'",
        )
    psql_hiver_request: HiverRequest | None = await db_session.find_one_or_none(
        model=HiverRequest,
        criteria=(
            Column("sender_guid") == user.guid,
            Column("receiver_guid") == user_guid,
        ),
    )
    # TODO: handle declined request!
    if psql_hiver_request and psql_hiver_request.status in (
        HiverRequestStatus.PENDING,
        HiverRequestStatus.ACCEPTED,
    ):
        raise APIException(
            api_context=USER_HIVER_API_CONTEXT,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A request to user with guid '{user_guid}' is alreadby been sent",
        )
    receiver: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("guid") == user_guid,),
    )
    if not receiver:
        raise APIException(
            api_context=USER_HIVER_API_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attempting to send a hiver request to a non existing user",
        )
    hiver_request = HiverRequest(
        sender_guid=user.guid,
        receiver_guid=user_guid,
    )
    await db_session.add(
        instance=hiver_request,
    )
    await esclient.add(
        index=settings.ES_HIVER_REQUESTS_INDEX,
        instance=ESHiverRequestBase(**hiver_request.model_dump()),
    )
    if receiver.fcm_token:
        await fcm.send_push_notification(
            fcm_token=receiver.fcm_token,
            title="You have a new hiver request",
            body=f"{user.username} want joining your hive",
            image_url=user.profile_image,
        )
    celery_send_hiver_request.apply_async(
        args=(
            hiver_request.model_dump(),
            user.username,
            user.profile_image,
            receiver.fcm_token,
        ),
        queue="partyup_public_users_queue",
        priority=3,
    )
    return hiver_request


async def get_user_profile(
    esclient: ElasticsearchClient,
    id: UUID,
) -> ESUser:
    es_user: ESUser = await esclient.get(
        index=settings.ES_USERS_INDEX,
        id=id,
        model=ESUser,
    )
    if not es_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find user in ES DB lined to doc id '{id}'",
        )
    return es_user


async def remove_hiver_request(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    user_guid: UUID,
): ...
