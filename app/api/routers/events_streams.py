import asyncio
from typing import Annotated, Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, Path, WebSocket, WebSocketDisconnect
from redis.asyncio.client import PubSub
from starlette import status

from app.api.exceptions.http_exc import APIException
from app.constants import USER_API_CONTEXT
from app.database.redis import RedisClient
from app.depends.depends import get_redis_client

wsrouter = APIRouter(prefix="/ws/stream/events")


@wsrouter.websocket(
    path="/{event_guid}",
    name="live-event-media-stream",
)
async def event_media_ws(
    websocket: Annotated[WebSocket, Any],
    event_guid: Annotated[UUID, Path(default=...)],
    redis_client: Annotated[RedisClient, Depends(dependency=get_redis_client)],
    # user: Annotated[User, Depends(dependency=admit_user)],
) -> None:
    """
    WebSocket connection for real-time media updates.
    Subscribes to Redis Pub/Sub channel for event media updates.
    """

    redis_set_key: str = f"event_users:{event_guid}"
    if not redis_client.redis.sismember(
        name=redis_set_key,
        value=str("fd04f528-d228-4d45-9e5c-74c10b7c6402"),
    ):
        raise APIException(
            api_context=USER_API_CONTEXT,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is not allowed to access event media stream",
        )
    pubsub: PubSub = redis_client.redis.pubsub()
    await pubsub.subscribe(f"event_media:{event_guid}")
    await websocket.accept()
    try:
        while True:
            message: Dict[str, Any] | None = await pubsub.get_message(
                ignore_subscribe_messages=True
            )
            if message and message["type"] == "message":
                await websocket.send_text(data=message["data"])
            await asyncio.sleep(delay=0.1)  # Prevents high CPU usage
    except WebSocketDisconnect:
        redis_client.redis.srem(
            redis_set_key, str("fd04f528-d228-4d45-9e5c-74c10b7c6402")
        )
        await pubsub.unsubscribe(f"event_media:{event_guid}")
