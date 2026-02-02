import asyncio
import json
from collections.abc import Callable
from types import CoroutineType
from typing import Any

import functions_framework
from cloudevents.http.event import CloudEvent

from cloud_funcs.public_users.funcs_map import MAPPER


@functions_framework.cloud_event
def handle_user_event(cloud_event: CloudEvent) -> None:
    message: dict[str, Any] = json.loads(cloud_event.data)
    event: str = message["event"]
    func: Callable[..., CoroutineType[Any, Any, None]] = MAPPER[event]
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    asyncio.run_coroutine_threadsafe(
        coro=func(message["data"]),
        loop=loop,
    )
