from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import auth as authfuncs
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.auth import FCMToken, FirebaseUser, Token
from app.datamodels.schemas.request import UserCreateBase
from app.depends.depends import (
    get_current_user,
    get_es_query_service,
    get_firebase_user,
)

router = APIRouter(prefix="/auth")


@router.post(
    path="/signup/email",
    status_code=status.HTTP_201_CREATED,
    description="Sign up a new user using email and password.",
)
async def sign_up_by_email(
    request: Annotated[Request, Any],
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user_form: Annotated[UserCreateBase, Body(default=...)],
) -> None:
    """
    Register a new user using an email and password.

    Args:
        request (Request): The incoming HTTP request object.
        session (AsyncSession): Database session dependency.
        user_form (UserCreateBase): User registration details.

    Returns:
        None
    """
    return await authfuncs.signup_user_by_email(
        esclient=esclient,
        request=request,
        db_session=db_session,
        user_form=user_form,
    )


@router.post(
    path="/signin/google",
    status_code=status.HTTP_200_OK,
    response_model=Token,
    description="Sign in or sign up a user using Google authentication.",
)
async def sign_up_by_google(
    esclient: Annotated[ElasticsearchClient, Depends(dependency=get_es_query_service)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    firebase_user: Annotated[FirebaseUser, Depends(dependency=get_firebase_user)],
    fcm_token: Annotated[FCMToken, Body(default=...)],
) -> Token:
    """
    Authenticate a user using Google Firebase authentication.
    If the user does not exist, they are registered automatically.

    Args:
        session (AsyncSession): Database session dependency.
        firebase_user (FirebaseUser): Authenticated Google user details.
        fcm_token (FCMToken): Firebase Cloud Messaging token for push notifications.

    Returns:
        Token: Authentication token for the session.
    """
    return await authfuncs.signin_or_signup_user_by_google(
        esclient=esclient,
        db_session=db_session,
        firebase_user=firebase_user,
        fcm_token=fcm_token,
    )


@router.post(
    path="/signin/email",
    status_code=status.HTTP_200_OK,
    response_model=Token,
    description="Authenticate a user using email and password.",
)
async def sign_in_by_email(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
    fcm_token: Annotated[FCMToken, Body(default=...)],
) -> Token:
    """
    Authenticate a user using their email and password.

    Args:
        user (User): The authenticated user object.
        fcm_token (FCMToken): Firebase Cloud Messaging token for push notifications.

    Returns:
        Token: Authentication token for the session.
    """
    return await authfuncs.signin_user_by_email(
        user=user,
        fcm_token=fcm_token,
    )


@router.post(
    path="/email-verification/resend",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Resend a verification email to an existing user.",
)
async def resend_email_verification(
    request: Annotated[Request, Any],
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
) -> None:
    """
    Resend an email verification link to a user.

    Args:
        request (Request): The incoming HTTP request object.
        user (User): The authenticated user requesting verification.

    Returns:
        None
    """
    await authfuncs.resend_email_verification(
        request=request,
        user=user,
    )


@router.post(
    path="/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Logout the currently authenticated user.",
)
async def logout_user(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
) -> None:
    """
    Logout the authenticated user.

    Args:
        user (User): The authenticated user.

    Returns:
        None
    """
    return await authfuncs.logout_user(
        user=user,
    )


@router.post(
    path="/fcm-token/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Refresh the Firebase Cloud Messaging (FCM) token for push notifications.",
)
async def refresh_fcm_token(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    user: Annotated[User, Depends(dependency=get_current_user)],
    fcm_token: Annotated[FCMToken, Body(default=...)],
) -> None:
    """
    Update the user's Firebase Cloud Messaging (FCM) token.

    Args:
        user (User): The authenticated user.
        fcm_token (FCMToken): The new FCM token for push notifications.

    Returns:
        None
    """
    return await authfuncs.refresh_user_fcm_token(
        user=user,
        fcm_token=fcm_token,
    )


@router.post(
    path="/password/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Reset the password of an authenticated user.",
)
async def reset_user_password(
    _: Annotated[AsyncSession, Depends(dependency=psql_session_manager)],
    request: Annotated[Request, Any],
    user: Annotated[User, Depends(dependency=get_current_user)],
) -> None:
    """
    Reset the password of an authenticated user.

    Args:
        request (Request): The incoming HTTP request object.
        user (User): The authenticated user requesting a password reset.

    Returns:
        None
    """
    return await authfuncs.reset_user_password(
        request=request,
        user=user,
    )
