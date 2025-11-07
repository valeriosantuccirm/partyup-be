import json
from typing import Any

from google.cloud import pubsub_v1  # pyright: ignore[reportMissingTypeStubs]

from app.config import settings
from app.configlog import logger
from producer.enums.topics import GCPTopics


async def publish_message(
    topic_name: GCPTopics,
    message: Any,
) -> None:
    publisher = pubsub_v1.PublisherClient()
    topic_path: str = publisher.topic_path(  # type: ignore
        project=settings.GOOGLE_PROJECT_ID,
        topic=topic_name.value,
    )
    publisher.publish(  # pyright: ignore[reportUnknownMemberType]
        topic=topic_path,
        data=json.dumps(message).encode("utf-8"),
    )
    logger.info(f"Published message to {topic_name}. Message: {message}")
