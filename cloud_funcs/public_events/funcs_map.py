from collections.abc import Callable
from types import CoroutineType
from typing import Any

from public_events.constants import EVENT_JOIN

from cloud_funcs.public_events.services.event_join import run_join_public_event

MAPPER: dict[str, Callable[..., CoroutineType[Any, Any, None]]] = {
    EVENT_JOIN: run_join_public_event,
}
