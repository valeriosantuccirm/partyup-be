from datetime import datetime
from typing import Any, List, Tuple

from sqlalchemy import ColumnElement
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import settings
from app.constants import AUTH_API_CONTEXT, DB_API_CONTEXT, DB_ES_DB_CONTEXT
from app.core.common import (
    are_user_info_complete,
    is_user_unique_params_already_assigned,
)
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.elasticsearch.queries import common_q
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_user import ESUser, ESUserBase
from app.database.models.enums.user import UserInfoStatus
from app.database.models.psql.user import User
from app.datamodels.schemas.request import UserRequestBaseModel


async def deactivate_account(
    user: User,
) -> None:
    """
    Delete a user from the database based on their GUID.

    Args:
        :user (User): The user object.

    Returns:
        :UUID: The GUID related to the deleted user row.

    Raises:
        :APIException: Gracefully handled exceptions.
    """
    user.is_active = False
    user.username = None
    user.logout_timestamp = datetime.now().replace(microsecond=0)


async def update_existing_user(
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    user: User,
    user_form: UserRequestBaseModel,
) -> User:
    """
    Update an existing user in the database.

    Args:
        :session (Session): The SQLAlchemy database session.
        :user_guid (UUID): The GUID related to the user row to be updated.
        :user_form (UserRequestBaseModel): The request model containing updated user data.

    Returns:
        :User: The updated user object.

    Raises:
        :APIException: Gracefully handled exceptions.
    """
    if not user.username and not user_form.username:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_409_CONFLICT,
            detail="User must have a unique username assigned",
        )
    is_username_allocated: bool = await is_user_unique_params_already_assigned(
        db_session=db_session,
        domain_attribute_pairs=(("username", user_form.username),),
    )
    if is_username_allocated and user.username != user_form.username:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username {user_form.username} is not assignable",
        )
    es_user: ESUser | None = await esclient.find(
        index=settings.ES_USERS_INDEX,
        query=common_q.find_by_attr(guid=user.guid),
        model=ESUser,
        one=True,
    )
    if not es_user:
        raise DBException(
            api_context=DB_API_CONTEXT,
            db_context=DB_ES_DB_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Could not find ES user linked to PSQL user with guid '{user.guid}'",
        )

    for k, v in user_form.model_dump().items():
        setattr(user, k, v)
    user.full_name = f"{user.first_name} {user.last_name}"
    user.user_info_status = (
        UserInfoStatus.COMPLETE
        if await are_user_info_complete(user=user)
        else UserInfoStatus.INCOMPLETE
    )
    user.updated_at = datetime.now()
    fileds: dict[str, Any] = {**es_user.model_dump(), **user.model_dump()}
    updated_es_user: ESUserBase = ESUserBase(**fileds)
    await esclient.update(
        index=settings.ES_USERS_INDEX,
        doc_id=es_user.id,
        **updated_es_user.model_dump(),
    )
    return user


async def find_user(
    db_session: PSQLSessionManager,
    filters: Tuple[Tuple[str, Any], ...] = (),
) -> User:
    """
    Retrieve an existing user from the database.

    Args:
        :session (AsyncSession): The database session to use for querying.
        filters (Tuple[Tuple[str, Any], ...], optional): A tuple containing pairs of attribute names and values to filter by. Defaults to ().

    Returns:
        :User: The existing user object if found.

    Raises:
        :APIException: Gracefully handled exceptions.
    """
    clauses: List[ColumnElement] = []
    for pair in filters:
        clauses.append(getattr(User, pair[0]) == pair[1])
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=clauses,
    )
    if not user:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
