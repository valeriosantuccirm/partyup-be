import json
from pathlib import Path
from typing import Any

from google.cloud.pubsub_v1 import (
    PublisherClient,
)
from google.cloud.pubsub_v1.publisher.futures import Future
from google.oauth2.service_account import Credentials
from pydantic import BaseModel

from app.config import settings


class Publisher:
    __publisher: PublisherClient = PublisherClient(
        credentials=Credentials.from_service_account_file(  # type: ignore
            f"{Path(__file__).resolve().cwd()!s}/.creds/partyup-be-privatekey-pubsub.json"
        )
    )
    __project_id: str = settings.GOOGLE_PROJECT_ID

    def __init__(
        self,
        topic_id: str,
    ) -> None:
        self.topic_id: str = topic_id

    @property
    def topic_path(self) -> str:
        return self.__publisher.topic_path(
            project=self.__project_id,
            topic=self.topic_id,
        )

    async def publish(
        self,
        data: Any,
    ) -> Future:
        if isinstance(data, BaseModel):
            data = data.model_dump()
        data_str: str = json.dumps(data)
        future: Future = self.__publisher.publish(  # type: ignore
            self.topic_path,
            data=data_str.encode("utf-8"),
        )
        return future  # pyright: ignore[reportUnknownVariableType]
