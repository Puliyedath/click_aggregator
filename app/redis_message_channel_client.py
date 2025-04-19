import redis.asyncio as redis
import os
import json


class RedisMessageChannelClient:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.redis_client = redis.Redis(
            host=self.host, port=self.port, password=self.password
        )
        self.pubsub = None

    async def publish_message(self, message: dict, chat_room_id: str):
        await self.redis_client.publish(chat_room_id, json.dumps(message))

    async def subscribe_to_chat_room(self, chat_room_ids: list[str]):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(*chat_room_ids)
        return pubsub

    async def close(self):
        await self.redis_client.close()
