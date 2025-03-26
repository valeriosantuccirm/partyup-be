from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import user as userfuncs
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.request import UserRequestBaseModel
from app.datamodels.schemas.response import UserResponseModel
from app.depends.depends import get_current_user, get_es_query_service

router = APIRouter(prefix="/users/me/profile")


@router.get(
    path="",
    description="Retrieve the details of the currently logged-in user.",
    status_code=status.HTTP_200_OK,
    response_model=UserResponseModel,
)
async def get_user_details(
    user: Annotated[User, Depends(dependency=get_current_user)],
) -> User:
    """
    Get the details of the authenticated user.

    Args:
        user (User): The currently logged-in user.

    Returns:
        UserResponseModel: The user details.
    """
    return user


@router.patch(
    path="/complete",
    description="Update and complete the user's profile with missing information.",
    status_code=status.HTTP_200_OK,
    response_model=UserResponseModel,
)
async def complete_user_profile(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
    user_form: Annotated[UserRequestBaseModel, Body(default=...)],
) -> User:
    """
    Complete the user's profile by adding missing information.

    Args:
        session (AsyncSession): Database session dependency.
        user (User): The currently authenticated user.
        user_form (UserRequestBaseModel): Data containing the additional user details.

    Returns:
        UserResponseModel: The updated user details.
    """
    return await userfuncs.update_existing_user(
        esclient=esclient,
        db_session=db_session,
        user=user,
        user_form=user_form,
    )


@router.delete(
    path="/deactivate",
    description="Deactivate the currently logged-in user. The account is not deleted.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_account(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
) -> None:
    """
    Deactivate the authenticated user account.

    This action does not delete the user from the database but marks the account as inactive.

    Args:
        user (User): The currently authenticated user.

    Returns:
        None
    """
    return await userfuncs.deactivate_account(user=user)
