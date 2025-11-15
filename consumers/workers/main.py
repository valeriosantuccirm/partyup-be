import json
from typing import Any

from google.cloud.pubsub_v1.subscriber.message import Message

from consumers.constants import (
    DAILY_PAYMENTS,
    EVENT_CANCEL,
    EVENT_INVITE_RSVP,
    EVENT_INVITE_SEND,
    EVENT_JOIN,
    EVENT_REVOKE,
    HIVER_REQUEST,
    HIVER_REQUEST_RESPOND,
    USER_CREATE,
    USER_FOLLOW,
    USER_UNFOLLOW,
    USER_UPDATE,
)
from jobs.hivers.hiver_respond_request import run_respond_hiver_request
from jobs.payments.main import process_daily_pending_payments
from jobs.public_events.event_join import run_join_public_event
from jobs.public_events.event_revoke import run_revoke_join_event
from jobs.public_users.hiver_request import run_send_hiver_request
from jobs.public_users.user_create import run_create_user
from jobs.public_users.user_follow import run_follow_user
from jobs.public_users.user_unfollow import run_unfollow_user
from jobs.user_events.event_cancel import run_cancel_user_event
from jobs.user_events.event_invite_rsvp import crun_rsvp_event_participation
from jobs.user_events.event_invite_send import run_send_event_invitations_to_hivers
from jobs.users.user_update import run_update_user


async def handle_pubsub_message(
    event: Message,
    context: dict[str, Any],
) -> None:
    """Triggered from a message on a Pub/Sub topic."""
    message: dict[str, Any] = json.loads(event.data)
    if message.get("event") == DAILY_PAYMENTS:
        await process_daily_pending_payments()
    if message.get("event") == USER_FOLLOW:
        await run_follow_user(
            msg_data=message["data"],
        )
    if message.get("event") == USER_CREATE:
        await run_create_user(
            msg_data=message["data"],
        )
    if message.get("event") == USER_UPDATE:
        await run_update_user(
            msg_data=message["data"],
        )
    if message.get("event") == USER_UNFOLLOW:
        await run_unfollow_user(
            msg_data=message["data"],
        )
    if message.get("event") == HIVER_REQUEST:
        await run_send_hiver_request(
            msg_data=message["data"],
        )
    if message.get("event") == EVENT_JOIN:
        await run_join_public_event(
            msg_data=message["data"],
        )
    if message.get("event") == EVENT_REVOKE:
        await run_revoke_join_event(
            msg_data=message["data"],
        )
    if message.get("event") == HIVER_REQUEST_RESPOND:
        await run_respond_hiver_request(
            msg_data=message["data"],
        )
    if message.get("event") == EVENT_INVITE_SEND:
        await run_send_event_invitations_to_hivers(
            msg_data=message["data"],
        )
    if message.get("event") == EVENT_INVITE_RSVP:
        await crun_rsvp_event_participation(
            msg_data=message["data"],
        )
    if message.get("event") == EVENT_CANCEL:
        await run_cancel_user_event(
            msg_data=message["data"],
        )
