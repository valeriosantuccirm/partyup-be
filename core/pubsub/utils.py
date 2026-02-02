from pydantic import (
    BaseModel,
    Field,
)

from core.pubsub.events.enums import EventsPubSubEvent
from core.pubsub.hivers.enums import HiversPubSubEvent
from core.pubsub.public_events.enums import PublicEventsPubSubEvent
from core.pubsub.public_users.enums import PublicUsersPubSubEvent

T = (
    PublicUsersPubSubEvent
    | PublicEventsPubSubEvent
    | HiversPubSubEvent
    | EventsPubSubEvent
)


class _BasePubSubMsg(BaseModel):  # pyright: ignore[reportUnusedClass]
    event: T = Field(default=...)
