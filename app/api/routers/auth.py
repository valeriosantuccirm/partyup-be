from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path, Request
from pydantic import StrictStr
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core.corefuncs import auth as authfuncs
from app.core.decorators import manage_transaction
from app.depends.depends import (
    get_current_user,
    get_firebase_user,
)
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.psql.user import User
from core.database.session import psqlclient
from core.datamodels.schemas.auth import FCMToken, FirebaseUser, Token
from core.datamodels.schemas.request import UserCreateBase

router = APIRouter(prefix="/auth")


@router.post(
    path="/signup/email",
    status_code=status.HTTP_201_CREATED,
    description="Sign up a new user using email and password.",
    response_model=User,
)
@manage_transaction
async def sign_up_by_email(
    request: Annotated[Request, Any],
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    user_form: Annotated[UserCreateBase, Body(default=...)],
) -> User:
    """
    Register a new user using an email and password.

    Args:
        request (Request): The incoming HTTP request object.
        db_session (AsyncSession): Database session dependency.
        user_form (UserCreateBase): User registration details.
    """
    return await authfuncs.signup_user_by_email(
        request=request,
        db_session=db_session,
        user_form=user_form,
    )


@router.post(
    path="/login/email",
    status_code=status.HTTP_200_OK,
    description="Login with `uername` and `password`.",
    response_model=User,
)
@manage_transaction
async def login_by_email_and_password(
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    email: Annotated[StrictStr, Body(default=...)],
    password: Annotated[StrictStr, Body(default=...)],
) -> User:
    """
    TODO: find the way
    """
    # c = await create_partyup_ticket(
    #     qrdata=QRData(
    #         event=BaseQRCodeData(
    #             name="Trasloco da Roma a Kufstein!",
    #             guid=uuid4(),
    #         ),
    #         attendee=BaseQRCodeData(
    #             name="Valerio Santucci",
    #             guid=uuid4(),
    #         ),
    #         creator=BaseQRCodeData(
    #             name="Erica Pitti",
    #             guid=uuid4(),
    #         ),
    #         payment=BaseQRCodePaymentData(
    #             status="success",
    #             amount=float(from_stripe_amount_cents(15089)),
    #             currency="EUR",
    #             timestamp=date.today() + timedelta(5),
    #         ),
    #     )
    # )
    return await authfuncs.login_with_eamil_and_pswd(
        db_session=db_session,
        email=email,
        password=password,
    )


@router.post(
    path="/signin/google",
    status_code=status.HTTP_200_OK,
    response_model=User,
    description="Sign in or sign up a user using Google authentication.",
)
@manage_transaction
async def sign_up_by_google(
    request: Request,
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
    firebase_user: Annotated[FirebaseUser, Depends(dependency=get_firebase_user)],
) -> User:
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
        db_session=db_session,
        firebase_user=firebase_user,
        fcm_token=request.headers["X-FCM-Token"],
    )


@router.post(
    path="/signin/email",
    status_code=status.HTTP_200_OK,
    response_model=Token,
    description="Authenticate a user using email and password.",
)
@manage_transaction
async def sign_in_by_email(
    request: Annotated[Request, Any],
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
    user: Annotated[User, Depends(dependency=get_current_user)],
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
        x_fcm_token=request.headers["X-FCM-Token"],
    )


@router.get(
    path="/{firebase_uid}/email-verification",
    status_code=status.HTTP_200_OK,
    description="Verify in app user email.",
)
@manage_transaction
async def verify_eamil(
    firebase_uid: Annotated[str, Path(default=...)],
    db_session: Annotated[PSQLClient, Depends(dependency=psqlclient)],
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
@manage_transaction
async def resend_email_verification(
    request: Annotated[Request, Any],
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
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
@manage_transaction
async def logout_user(
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
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


@router.put(
    path="/fcm-token/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Refresh the Firebase Cloud Messaging (FCM) token for push notifications.",
)
@manage_transaction
async def refresh_fcm_token(
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
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
@manage_transaction
async def reset_user_password(
    _: Annotated[AsyncSession, Depends(dependency=psqlclient)],
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


@router.put(
    path="/token/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Refresh the Firebase Cloud Messaging (FCM) token for push notifications.",
)
@manage_transaction
async def refresh_token(
    user: Annotated[User, Depends(dependency=get_current_user)],
    access_token: Annotated[StrictStr | None, Body(default=...)] = None,
    fcm_token: Annotated[StrictStr | None, Body(default=...)] = None,
) -> None:
    """
    Update the user's Firebase Cloud Messaging (FCM) token.

    Args:
        user (User): The authenticated user.
        fcm_token (FCMToken): The new FCM token for push notifications.

    Returns:
        None
    """
    return await authfuncs.refresh_user_access_token(
        user=user,
        access_token=access_token,
        fcm_token=fcm_token,
    )
