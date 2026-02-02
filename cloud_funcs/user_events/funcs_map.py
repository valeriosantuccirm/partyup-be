from collections.abc import Callable
from types import CoroutineType
from typing import Any

from user_events.constants import (
    EVENT_CANCEL,
    EVENT_INVITE_RSVP,
    EVENT_INVITE_SEND,
)

from cloud_funcs.user_events.services.event_cancel import run_cancel_user_event
from cloud_funcs.user_events.services.event_invite_rsvp import (
    crun_rsvp_event_participation,
)
from cloud_funcs.user_events.services.event_invite_send import (
    run_send_event_invitations_to_hivers,
)

MAPPER: dict[str, Callable[..., CoroutineType[Any, Any, None]]] = {
    EVENT_CANCEL: run_cancel_user_event,
    EVENT_INVITE_RSVP: crun_rsvp_event_participation,
    EVENT_INVITE_SEND: run_send_event_invitations_to_hivers,
}
