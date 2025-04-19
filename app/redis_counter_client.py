from typing import AsyncGenerator
from fastapi import Request
import redis.asyncio as redis

STOPWORD = "STOP"

CHANNEL = "counter_updates"


class CounterRedisClient:
    def __init__(self, host: str, port: int, password: str):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
        )
        self.counter_key = "fastapi_counter"

    async def increment_counter(self) -> int:
        new_count = await self.redis_client.incr(self.counter_key)
        await self.redis_client.publish(CHANNEL, new_count)
        return new_count

    async def get_counter(self) -> int:
        return await self.redis_client.get(self.counter_key)

    async def reset_counter(self) -> None:
        await self.redis_client.set(self.counter_key, 0)

    async def publish_counter(self, count: int) -> None:
        try:
            await self.redis_client.publish(CHANNEL, count)
        except Exception as e:
            print(f"Error publishing counter: {e}")
            raise

    async def async_counter_reader(self, request: Request) -> AsyncGenerator[int, None]:
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    if message["data"] == STOPWORD:
                        break
                    counter_value = int(message["data"])
                    # Stream the counter value to browser clients
                    yield f"data: {counter_value}\n\n"
                if await request.is_disconnected():
                    break
        except Exception as e:
            print(f"Error reading from channel: {e}")
            raise
        finally:
            await pubsub.unsubscribe(CHANNEL)

    async def close(self) -> None:
        await self.redis_client.close()
