import os
from datetime import datetime
from typing import Any

import httpx
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request
from firebase_admin import auth
from firebase_admin._user_mgt import (
    UserRecord,
)
from sqlalchemy import Column
from starlette import status

from app.core import common as coreutils
from app.core.email import Email
from core.config import ph, redis, settings
from core.database.crud.psql.psqlclient import PSQLClient
from core.database.models.enums.common import OAuthProvider
from core.database.models.enums.user import UserInfoStatus
from core.database.models.psql.user import User
from core.datamodels.schemas.auth import FCMToken, FirebaseUser, Token
from core.datamodels.schemas.request import UserCreateBase
from core.pubsub.public_users.enums import PublicUsersPubSubEvent
from core.pubsub.public_users.schemas import UserCreatePubSubMsg
from core.pubsub.publisher import Publisher


async def signup_user_by_email(
    request: Request,
    db_session: PSQLClient,
    user_form: UserCreateBase,
) -> User:
    if await coreutils.is_user_unique_params_already_assigned(
        db_session=db_session,
        domain_attribute_pairs=(("email", user_form.email),),
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already in use",
        )
    try:
        firebase_user: UserRecord = auth.get_user_by_email(
            email=user_form.email,
        )
    except auth.UserNotFoundError:
        firebase_user: UserRecord = auth.create_user(
            email=user_form.email,
            email_verified=False,
        )
    user: User = User(
        email=user_form.email.lower(),
        email_verified=firebase_user.email_verified,
        firebase_uid=firebase_user.uid,  # pyright: ignore[reportArgumentType] According to 'firebase_admin' doc this is never None
        is_active=True,
        user_info_status=UserInfoStatus.INCOMPLETE,
        auth_provider=OAuthProvider.EMAIL,
        profile_image=firebase_user.photo_url,
        hashed_pswd=ph.hash(user_form.hashed_psw),
        fcm_token=request.headers.get("X-FCM-Token"),
    )
    if not user.email_verified:
        sender = Email(
            request=request,
            user_email=user.email,
        )
        await sender.send_verification_email(
            firebase_uid=user.firebase_uid,
        )
    await db_session.add(
        instance=user,
    )
    publisher = Publisher(
        topic_id=settings.GOOGLE_ELASTIC_USERS_TOPIC_ID,
    )
    await publisher.publish(
        UserCreatePubSubMsg(
            event=PublicUsersPubSubEvent.user_create,
            data=user,
        )
    )
    return user


async def resend_email_verification(
    request: Request,
    user: User,
) -> None:
    if user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email already verified",
        )
    sender = Email(
        request=request,
        user_email=user.email,
    )
    await sender.send_verification_email(
        firebase_uid=user.firebase_uid,
    )


async def signin_or_signup_user_by_google(
    db_session: PSQLClient,
    firebase_user: FirebaseUser,
    fcm_token: str,
) -> User:
    # Check if user exists
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("email") == firebase_user.email,),
    )
    if user and (user.auth_provider != OAuthProvider.GOOGLE or not user.fcm_token):
        user.auth_provider = OAuthProvider.GOOGLE
        user.profile_image = firebase_user.profile_picture_url
        user.email_verified = True
        user.fcm_token = fcm_token
    if not user:
        user = User(
            email=firebase_user.email.lower(),
            email_verified=True,  # Google has always verified email for users
            firebase_uid=firebase_user.uid,
            is_active=True,
            user_info_status=UserInfoStatus.INCOMPLETE,
            auth_provider=OAuthProvider.GOOGLE,
            profile_image=firebase_user.profile_picture_url,
            fcm_token=fcm_token,
            full_name=firebase_user.full_name,
            hashed_pswd="TO REMOVE AS MANDATORY FIELD WHEN GOOGLE SIGNUP AND ASK TO ADD LATER MAYBE",  # TODO
        )
        await db_session.add(
            instance=user,
        )
        publisher = Publisher(
            topic_id=settings.GOOGLE_ELASTIC_USERS_TOPIC_ID,
        )
        await publisher.publish(
            UserCreatePubSubMsg(
                event=PublicUsersPubSubEvent.user_create,
                data=user,
            )
        )
    return user


async def signin_user_by_email(
    user: User,
    x_fcm_token: str,
) -> Token:
    # Check email verification status
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Cannot sign in",
        )
    if not user.fcm_token:
        user.fcm_token = x_fcm_token
    user.auth_provider = OAuthProvider.EMAIL
    cached_access_token: Any = redis.get(name=f"access_token:{user.firebase_uid}")
    return Token(access_token=str(cached_access_token))


async def logout_user(
    user: User,
) -> None:
    user.logout_timestamp = datetime.now()
    user.fcm_token = None
    redis.delete(f"access_token:{user.firebase_uid}")


async def refresh_user_fcm_token(
    user: User,
    fcm_token: FCMToken,
) -> None:
    user.fcm_token = fcm_token.fcm_token


async def refresh_user_access_token(
    user: User,
    access_token: str | None = None,
    fcm_token: str | None = None,
) -> None:
    if access_token:
        redis.set(
            name=f"access_token:{user.firebase_uid}",
            value=access_token,
            ex=3000,
        )  # 50 mins
    if fcm_token:
        user.fcm_token = fcm_token


async def reset_user_password(
    request: Request,
    user: User,
) -> None:
    auth.generate_password_reset_link(email=user.email)
    sender = Email(
        request=request,
        user_email=user.email,
    )
    await sender.send_reset_password_link()


async def verify_in_app_email(
    db_session: PSQLClient,
    firebase_uid: str,
) -> None:
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("firebase_uid") == firebase_uid,),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.email_verified = True
    await db_session.update(user)


async def login_with_eamil_and_pswd(
    db_session: PSQLClient,
    email: str,
    password: str,
) -> User:
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("email") == email,),
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        ph.verify(user.hashed_pswd, password)
        API_KEY = os.environ[
            "FIREBASE_WEB_API_KEY"
        ]  # ← From Firebase Console > Project Settings
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True,
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
                json=payload,
            )
            res.raise_for_status()
        id_token: str = res.json()["idToken"]
        firebase_user: UserRecord = auth.get_user(uid=user.firebase_uid)
        redis.set(
            name=f"access_token:{firebase_user.uid}",
            value=id_token,
            ex=3000,
        )  # 50 mins
        return user
    except VerifyMismatchError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missmatch in verification. process",
        ) from e
