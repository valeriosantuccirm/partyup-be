from datetime import date, timedelta
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Path, Request
from pydantic import StrictStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import auth as authfuncs
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.psql.user import User
from app.database.session import psql_session_manager
from app.datamodels.schemas.auth import FCMToken, FirebaseUser, Token
from app.datamodels.schemas.request import UserCreateBase
from app.datamodels.utils import from_stripe_amount_cents
from app.depends.depends import (
    get_current_user,
    get_es_query_service,
    get_firebase_user,
)
from pubsub_workers.payments.src.qrcode.generator import create_partyup_ticket
from pubsub_workers.payments.src.schema.qr_data import (
    BaseQRCodeData,
    BaseQRCodePaymentData,
    QRData,
)

router = APIRouter(prefix="/auth")


@router.post(
    path="/signup/email",
    status_code=status.HTTP_201_CREATED,
    description="Sign up a new user using email and password.",
)
async def sign_up_by_email(
    request: Annotated[Request, Any],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    user_form: Annotated[UserCreateBase, Body(default=...)],
) -> None:
    """
    Register a new user using an email and password.

    Args:
        request (Request): The incoming HTTP request object.
        db_session (AsyncSession): Database session dependency.
        user_form (UserCreateBase): User registration details.
    """
    await authfuncs.signup_user_by_email(
        request=request,
        db_session=db_session,
        user_form=user_form,
    )


@router.post(
    path="/login/email",
    status_code=status.HTTP_200_OK,
    description="Login with `uername` and `password`.",
)
async def login_by_email_and_password(
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
    email: Annotated[StrictStr, Body(default=...)],
    password: Annotated[StrictStr, Body(default=...)],
) -> Token:
    """
    TODO: find the way
    """
    EMAIL = "valerio.santucci@gmail.com"
    PSWD = "12romanistA!"
    c = await create_partyup_ticket(
        qrdata=QRData(
            event=BaseQRCodeData(
                name="Trasloco da Roma a Kufstein!",
                guid=uuid4(),
            ),
            attendee=BaseQRCodeData(
                name="Valerio Santucci",
                guid=uuid4(),
            ),
            creator=BaseQRCodeData(
                name="Erica Pitti",
                guid=uuid4(),
            ),
            payment=BaseQRCodePaymentData(
                status="success",
                amount=float(from_stripe_amount_cents(15089)),
                currency="EUR",
                timestamp=date.today() + timedelta(5),
            ),
        )
    )
    return await authfuncs.login_with_eamil_and_pswd(
        db_session=db_session,
        # email=email,
        # password=password,
        email=EMAIL,
        password=PSWD,
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
        db_session (AsyncSession): Database session dependency.
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


@router.get(
    path="/{firebase_uid}/email-verification",
    status_code=status.HTTP_200_OK,
    description="Verify in app user email.",
)
async def verify_eamil(
    firebase_uid: Annotated[str, Path(default=...)],
    db_session: Annotated[PSQLSessionManager, Depends(dependency=psql_session_manager)],
) -> None:
    """
    Verify in app user email as redirect URL after Firebase email authentication.

    Args:
        firebase_uid (str): The Firebase id associated to the user.
        db_session (AsyncSession): Database session dependency.

    Returns:
        None
    """
    await authfuncs.verify_in_app_email(
        db_session=db_session,
        firebase_uid=firebase_uid,
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
