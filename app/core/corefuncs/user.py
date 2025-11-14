from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import ColumnElement
from starlette import status

from app.core.common import (
    are_user_info_complete,
    is_user_unique_params_already_assigned,
)
from app.database.crud.psql.psqlclient import PSQLClient
from app.database.models.elasticsearch.es_user import ESUserBase
from app.database.models.enums.user import UserInfoStatus
from app.database.models.psql.user import User
from app.datamodels.schemas.request import UserRequestBaseModel
from app.pubsub.public_users.enums import PublicUsersPubSubEvent
from app.pubsub.public_users.schemas import UserCreatePubSubMsg
from app.pubsub.publisher import Publisher


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
        :HTTPException: Gracefully handled exceptions.
    """
    user.is_active = False
    user.username = None
    user.logout_timestamp = datetime.now().replace(microsecond=0)
    publisher = Publisher(topic_id="")
    await publisher.publish(
        UserCreatePubSubMsg(
            event=PublicUsersPubSubEvent.user_deactivate,
            data=ESUserBase(
                **dict(**user.model_dump()),
            ),
        )
    )


async def update_existing_user(
    db_session: PSQLClient,
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
        :HTTPException: Gracefully handled exceptions.
    """
    if not user.username and not user_form.username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User must have a unique username assigned",
        )
    is_username_allocated: bool = await is_user_unique_params_already_assigned(
        db_session=db_session,
        domain_attribute_pairs=(("username", user_form.username),),
    )
    if is_username_allocated and user.username != user_form.username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username {user_form.username} is not assignable",
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
    publisher = Publisher(topic_id="")
    await publisher.publish(
        UserCreatePubSubMsg(
            event=PublicUsersPubSubEvent.user_update,
            data=ESUserBase(
                **dict(**user.model_dump()),
            ),
        )
    )
    return user


async def find_user(
    db_session: PSQLClient,
    filters: tuple[tuple[str, Any], ...] = (),
) -> User:
    """
    Retrieve an existing user from the database.

    Args:
        :session (AsyncSession): The database session to use for querying.
        filters (Tuple[Tuple[str, Any], ...], optional): A tuple containing pairs of attribute names and values to filter by. Defaults to ().

    Returns:
        :User: The existing user object if found.

    Raises:
        :HTTPException: Gracefully handled exceptions.
    """
    clauses: list[ColumnElement] = []
    for pair in filters:
        clauses.append(getattr(User, pair[0]) == pair[1])
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=clauses,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
