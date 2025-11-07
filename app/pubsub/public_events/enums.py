from enum import Enum


class PublicEventsPubSubEvent(Enum):
    event_join = "EVENT-JOIN"
    event_revoke = "EVENT-REVOKE"
