import json
from pathlib import Path
from typing import Any

from google.cloud.pubsub_v1 import (
    PublisherClient,
)
from google.cloud.pubsub_v1.publisher.futures import Future
from google.oauth2.service_account import Credentials

from app.config import settings


class Publisher:
    __publisher: PublisherClient = PublisherClient(
        credentials=Credentials.from_service_account_file(
            f"{Path(__file__).resolve().cwd()!s}/.creds/partyup-be-privatekey-pubsub.json"
        )
    )

    def __init__(
        self,
        project_id: str,
        topic_id: str,
    ) -> None:
        self.project_id: str = project_id
        self.topic_id: str = topic_id

    @property
    def topic_path(self) -> str:
        return self.__publisher.topic_path(
            project=self.project_id,
            topic=self.topic_id,
        )

    async def publish(self, data: Any) -> Future:
        data_str: str = json.dumps(data)
        future: Future = self.__publisher.publish(
            self.topic_path,
            data=data_str.encode("utf-8"),
        )
        return future


es_user_publisher = Publisher(
    project_id=settings.GOOGLE_PROJECT_ID,
    topic_id=settings.GOOGLE_ELASTIC_USERS_TOPIC_ID,
)
