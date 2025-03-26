from typing import Annotated, List, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from starlette import status

from app.core.corefuncs import user_hivers
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_hiver_request import ESHiverRequest
from app.database.models.enums.hiver import HiverRequestStatus
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.response import PaginatedListedUser
from app.depends.depends import admit_user, get_es_query_service

router = APIRouter(prefix="/users/me/hivers")


@router.put(
    path="/requests/{hiver_request_guid}/respond",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Respond to a friend request (accept or reject).",
)
async def respond_to_hiver_request(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=admit_user)],
    hiver_request_guid: Annotated[UUID, Path(default=...)],
    accept: Annotated[bool, Query(default=...)],
) -> None:
    """
    Accept or reject a friend request.

    Args:
        session (AsyncSession): The database session.
        user (User): The authenticated user.
        hiver_request_guid (UUID): The unique ID of the friend request.
        accept (bool): Whether to accept (True) or reject (False) the request.

    Returns:
        None
    """
    await user_hivers.respond_hiver_request(
        esclient=esclient,
        db_session=db_session,
        user=user,
        hiver_request_guid=hiver_request_guid,
        accept=accept,
    )


@router.get(
    path="/requests",
    response_model=List[ESHiverRequest],
    status_code=status.HTTP_200_OK,
    description="Retrieve sent or received friend requests.",
)
async def get_user_hivers_requests(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    user: Annotated[User, Depends(dependency=admit_user)],
    mode: Annotated[Literal["sent", "received"], Query(default=...)],
    status: Annotated[
        HiverRequestStatus, Query(default=...)
    ] = HiverRequestStatus.PENDING,
    limit: Annotated[int, Query(default=...)] = 20,
    offset: Annotated[int, Query(default=...)] = 0,
) -> List[ESHiverRequest]:
    """
    Retrieve a list of friend requests sent or received by the user.

    Args:
        user (User): The authenticated user.
        mode (Literal["sent", "received"]): Whether to retrieve sent or received requests.
        status (HiverRequestStatus): Filter requests by their status.
        limit (int): The number of requests to return.
        offset (int): Pagination offset.

    Returns:
        List[ESHiverRequest]: A list of friend requests matching the filters.
    """
    return await user_hivers.get_user_hiver_requests(
        esclient=esclient,
        user=user,
        status=status,
        mode=mode,
        limit=limit,
        offset=offset,
    )


@router.get(
    path="",
    response_model=PaginatedListedUser,
    status_code=status.HTTP_200_OK,
    description="Retrieve a paginated list of linked friends.",
)
async def get_user_linked_hivers(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    user: Annotated[User, Depends(dependency=admit_user)],
    limit: Annotated[int, Query(default=...)] = 20,
    offset: Annotated[int, Query(default=...)] = 0,
) -> PaginatedListedUser:
    """
    Retrieve a paginated list of linked friends (Hivers).

    Args:
        user (User): The authenticated user.
        limit (int): The number of linked friends to return.
        offset (int): Pagination offset.

    Returns:
        PaginatedListedUser: A paginated list of linked friends.
    """
    return await user_hivers.get_user_linked_hivers(
        esclient=esclient,
        user=user,
        limit=limit,
        offset=offset,
    )
