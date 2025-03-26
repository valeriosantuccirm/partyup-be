from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from pydantic import StrictStr
from starlette import status

from app.core.corefuncs import public_users
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_user import ESUser
from app.database.models.psql.hiver_request import HiverRequest
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.response import PaginatedListedUser
from app.depends.depends import admit_user, get_es_query_service

router = APIRouter(prefix="/users/public")


@router.get(
    path="/search",
    response_model=PaginatedListedUser,
    status_code=status.HTTP_200_OK,
    description="Search for users based on input, optional location, and radius.",
)
async def search_accounts(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    user: Annotated[User, Depends(dependency=admit_user)],
    user_input: Annotated[StrictStr, Query(default=...)],
    lat: Annotated[float | None, Query(default=...)] = None,
    lon: Annotated[float | None, Query(default=...)] = None,
    radius: Annotated[int, Query(default=...)] = 50,
    limit: Annotated[int, Query(default=...)] = 20,
    offset: Annotated[int, Query(default=...)] = 0,
) -> PaginatedListedUser:
    """
    Search for users.

    Args:
        user (User): The authenticated user.
        user_input (StrictStr): Search query.
        lat (float | None): Latitude for filtering results by location.
        lon (float | None): Longitude for filtering results by location.
        radius (int): Search radius in km.
        limit (int): Number of results to return.
        offset (int): Pagination offset.

    Returns:
        PaginatedListedUser: A paginated list of user accounts matching the criteria.
    """
    return await public_users.search_accounts(
        esclient=esclient,
        user=user,
        lat=lat,
        lon=lon,
        radius=radius,
        user_input=user_input,
        limit=limit,
        offset=offset,
    )


@router.get(
    path="/{id}/board",
    response_model=ESUser,
    status_code=status.HTTP_200_OK,
    description="Retrieve a user's public profile board based on visibility settings.",
)
async def get_user_board_by_visibility(
    _: Annotated[User, Depends(dependency=admit_user)],
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    id: Annotated[UUID, Path(default=...)],
) -> ESUser:
    """
    Get a user's public profile board.

    Args:
        id (UUID): The user's unique identifier.

    Returns:
        ESUser: The user's public profile information.
    """
    return await public_users.get_user_profile(
        esclient=esclient,
        id=id,
    )


@router.post(
    path="/{user_guid}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Follow another user.",
)
async def follow_user(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    user_guid: Annotated[UUID, Path(default=...)],
) -> None:
    """
    Follow a user.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        user_guid (UUID): The unique ID of the user to follow.

    Returns:
        None
    """
    await public_users.follow_user(
        esclient=esclient,
        db_session=db_session,
        user=user,
        user_guid=user_guid,
    )


@router.delete(
    path="/{user_guid}/unfollow",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Unfollow a user.",
)
async def unfollow_user(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    user_guid: Annotated[UUID, Path(default=...)],
) -> None:
    """
    Unfollow a user.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        user_guid (UUID): The unique ID of the user to unfollow.

    Returns:
        None
    """
    await public_users.unfollow_user(
        esclient=esclient,
        db_session=db_session,
        user=user,
        user_guid=user_guid,
    )


@router.post(
    path="/{user_guid}/send-hiver-request",
    response_model=HiverRequest,
    status_code=status.HTTP_201_CREATED,
    description="Send a hiver request to another user.",
)
async def send_hiver_request_to_user(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    user_guid: Annotated[UUID, Path(default=...)],
) -> HiverRequest:
    """
    Send a hiver request to another user.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        user_guid (UUID): The unique ID of the recipient user.

    Returns:
        HiverRequest: The created hiver request.
    """
    return await public_users.send_hiver_request(
        esclient=esclient,
        db_session=db_session,
        user=user,
        user_guid=user_guid,
    )


@router.delete(
    path="/{user_guid}/remove-hiver",
    status_code=status.HTTP_200_OK,
    description="Remove a user from your Hiver list.",
)
async def remove_hiver(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    user_guid: Annotated[UUID, Path(default=...)],
) -> None:
    """
    Remove a user from your Hiver list.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        user_guid (UUID): The unique ID of the user to remove.

    Returns:
        None.
    """
    return await public_users.remove_hiver_request(
        esclient=esclient,
        db_session=db_session,
        user=user,
        user_guid=user_guid,
    )
