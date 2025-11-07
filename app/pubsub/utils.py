from pydantic import (
    BaseModel,
    Field,
)

from app.pubsub.events.enums import EventsPubSubEvent
from app.pubsub.hivers.enums import HiversPubSubEvent
from app.pubsub.public_events.enums import PublicEventsPubSubEvent
from app.pubsub.public_users.enums import PublicUsersPubSubEvent

T = (
    PublicUsersPubSubEvent
    | PublicEventsPubSubEvent
    | HiversPubSubEvent
    | EventsPubSubEvent
)


class _BasePubSubMsg(BaseModel):  # pyright: ignore[reportUnusedClass]
    event: T = Field(default=...)
