from collections.abc import Callable
from types import CoroutineType
from typing import Any

from cloud_funcs.hivers.constants import HIVER_REQUEST_RESPOND
from cloud_funcs.hivers.services.hiver_respond_request import run_respond_hiver_request

MAPPER: dict[str, Callable[..., CoroutineType[Any, Any, None]]] = {
    HIVER_REQUEST_RESPOND: run_respond_hiver_request,
}
