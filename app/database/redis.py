from redis.asyncio import Redis, from_url

from app.config import settings


class RedisClient:
    def __init__(self) -> None:
        self.redis: Redis | None = None

    async def connect(self) -> None:
        self.redis = await from_url(
            url=settings.REDIS_URI,
            decode_responses=True,
        )

    async def publish(self, channel: str, message: str) -> None:
        """Publish a message to a Redis channel."""
        if self.redis:
            await self.redis.publish(
                channel=channel,
                message=message,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()


redis_client = RedisClient()
