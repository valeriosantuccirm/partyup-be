from collections.abc import Callable
from types import CoroutineType
from typing import Any

from public_users.constants import (
    HIVER_REQUEST,
    USER_CREATE,
    USER_FOLLOW,
    USER_UNFOLLOW,
)

from cloud_funcs.public_users.services.hiver_request import run_send_hiver_request
from cloud_funcs.public_users.services.user_create import run_create_user
from cloud_funcs.public_users.services.user_follow import run_follow_user
from cloud_funcs.public_users.services.user_unfollow import run_unfollow_user

MAPPER: dict[str, Callable[..., CoroutineType[Any, Any, None]]] = {
    USER_FOLLOW: run_follow_user,
    USER_UNFOLLOW: run_unfollow_user,
    USER_CREATE: run_create_user,
    HIVER_REQUEST: run_send_hiver_request,
}
