from enum import Enum


class EventsPubSubEvent(Enum):
    event_cancel = "EVENT-CANCEL"
    event_invite_send = "EVENT-INVITE-SEND"
    event_invite_rsvp = "EVENT-INVITE-RSVP"
