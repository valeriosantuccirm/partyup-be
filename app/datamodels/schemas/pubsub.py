from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    field_serializer,
)

from app.database.models.elasticsearch.es_user import ESUser, ESUserBase


class PubSubUserMsg(BaseModel):
    """
    Model representing the user GCP Pub/Sub schema.

    Attributes:


    """

    event: Literal["create", "delete", "update"] = Field(default=...)
    instance: ESUser | ESUserBase = Field(default=...)

    @field_serializer("instance")
    def _dump(self, model: BaseModel) -> dict[str, Any]:
        return model.model_dump()
