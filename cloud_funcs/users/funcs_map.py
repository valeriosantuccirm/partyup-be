from collections.abc import Callable
from types import CoroutineType
from typing import Any

from users.constants import USER_UPDATE

from cloud_funcs.users.services.user_update import run_update_user

MAPPER: dict[str, Callable[..., CoroutineType[Any, Any, None]]] = {
    USER_UPDATE: run_update_user,
}
