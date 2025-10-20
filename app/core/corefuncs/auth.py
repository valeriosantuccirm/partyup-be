import os
from datetime import datetime
from typing import Any

import requests
from argon2.exceptions import VerifyMismatchError
from fastapi import Request
from firebase_admin import auth
from firebase_admin._user_mgt import (
    UserRecord,
)
from sqlalchemy import Column
from starlette import status

from app.api.exceptions.http_exc import APIException, DBException
from app.config import ph, redis
from app.constants import AUTH_API_CONTEXT
from app.core import common as coreutils
from app.core.email import Email
from app.core.fcm import send_push_notification
from app.database.crud.elasticsearch.esclient import ElasticsearchClient
from app.database.crud.psql.session_manager import PSQLSessionManager
from app.database.models.elasticsearch.es_user import ESUserBase
from app.database.models.enums.common import OAuthProvider
from app.database.models.enums.user import UserInfoStatus
from app.database.models.psql.user import User
from app.datamodels.schemas.auth import FCMToken, FirebaseUser, Token
from app.datamodels.schemas.pubsub import PubSubUserMsg
from app.datamodels.schemas.request import UserCreateBase
from app.publisher import es_user_publisher


async def signup_user_by_email(
    request: Request,
    db_session: PSQLSessionManager,
    user_form: UserCreateBase,
) -> None:
    if await coreutils.is_user_unique_params_already_assigned(
        db_session=db_session,
        domain_attribute_pairs=(
            ("username", user_form.username),
            ("email", user_form.email),
        ),
    ):
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already in use",
        )
    firebase_user: UserRecord = auth.create_user(
        email=user_form.email,
        password=user_form.hashed_psw,
    )
    user: User = User(
        email=user_form.email,
        email_verified=firebase_user.email_verified,
        firebase_uid=firebase_user.uid,  # pyright: ignore[reportArgumentType] According to 'firebase_admin' doc this is never None
        is_active=True,
        user_info_status=UserInfoStatus.INCOMPLETE,
        auth_provider=OAuthProvider.EMAIL,
        profile_image=firebase_user.photo_url,
        username=user_form.username,
        hashed_pswd=ph.hash(user_form.hashed_psw),
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
    await es_user_publisher.publish(
        PubSubUserMsg(
            event="create",
            instance=ESUserBase(
                **dict(user),
            ),
        ).model_dump()
    )


async def resend_email_verification(
    request: Request,
    user: User,
) -> None:
    if user.email_verified:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
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
    esclient: ElasticsearchClient,
    db_session: PSQLSessionManager,
    firebase_user: FirebaseUser,
    fcm_token: FCMToken,
) -> Token:
    # Check if user exists
    psql_user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("email") == firebase_user.email,),
    )
    if psql_user and (
        psql_user.auth_provider != OAuthProvider.GOOGLE or not psql_user.fcm_token
    ):
        psql_user.auth_provider = OAuthProvider.GOOGLE
        psql_user.profile_image = firebase_user.profile_picture_url
        psql_user.email_verified = True
        psql_user.fcm_token = fcm_token.fcm_token
    if not psql_user:
        user: User = User(
            email=firebase_user.email,
            email_verified=True,  # Google has always verified email for users
            firebase_uid=firebase_user.uid,
            is_active=True,
            user_info_status=UserInfoStatus.INCOMPLETE,
            auth_provider=OAuthProvider.GOOGLE,
            profile_image=firebase_user.profile_picture_url,
            fcm_token=fcm_token.fcm_token,
            full_name=firebase_user.full_name,
        )
        await db_session.add(
            instance=user,
        )
        await es_user_publisher.publish(
            PubSubUserMsg(
                event="create",
                instance=ESUserBase(
                    **dict(user),
                ),
            ).model_dump()
        )
    return Token(access_token=firebase_user.access_token)


async def signin_user_by_email(
    user: User,
    fcm_token: FCMToken,
) -> Token:
    # Check email verification status
    if not user.email_verified:
        raise APIException(
            api_context=AUTH_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified. Cannot sign in",
        )
    if not user.fcm_token:
        user.fcm_token = fcm_token.fcm_token
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
    await send_push_notification(
        fcm_token=fcm_token.fcm_token,
        title="TEST",
        body="TEST SU TEST",
        image_url=user.profile_image,
    )
    user.fcm_token = fcm_token.fcm_token


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
    db_session: PSQLSessionManager,
    firebase_uid: str,
) -> None:
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("firebase_uid") == firebase_uid,),
    )
    if not user:
        raise DBException()

    user.email_verified = True
    await db_session.update(user)


async def login_with_eamil_and_pswd(
    db_session: PSQLSessionManager,
    email: str,
    password: str,
) -> Token:
    user: User | None = await db_session.find_one_or_none(
        model=User,
        criteria=(Column("email") == email,),
    )
    if not user:
        raise DBException()
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
        res = requests.post(
            f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}",
            json=payload,
        )
        res.raise_for_status()
        id_token = res.json()["idToken"]
        firebase_user: UserRecord = auth.get_user(uid=user.firebase_uid)
        redis.set(
            name=f"access_token:{firebase_user.uid}",
            value=id_token,
            ex=600,
        )  # 10 mins
        return Token(access_token=id_token)
    except VerifyMismatchError as e:
        raise APIException(
            api_context="auth",
        ) from e
