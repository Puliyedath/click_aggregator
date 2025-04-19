import time
from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from app import redis_message_channel_client
from app.redis_counter_client import CounterRedisClient
import os
import signal
import sys
import asyncio
from contextlib import asynccontextmanager

from app.redis_message_channel_client import RedisMessageChannelClient

fastapi_counter = CounterRedisClient(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
)

redis_message_channel_client = RedisMessageChannelClient(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("Shutting down...")
    await fastapi_counter.close()


app = FastAPI(lifespan=lifespan)


class Counter(BaseModel):
    count: int


counter = Counter(count=0)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/send-message")
async def send_message(request: Request):
    payload = await request.json()
    data = payload.get("data")
    message = data.get("message")
    chat_room_id = data.get("chat_room_id")
    assert message is not None, "Message is required"
    assert chat_room_id is not None, "Chat room ID is required"
    message_dict = {"message": message, "chat_room_id": chat_room_id}
    await redis_message_channel_client.publish_message(message_dict, chat_room_id)
    return {"status": "success", "message": "Message sent successfully"}


@app.get("/counter/{count}")
async def get_counter(count: int = 0):
    if count == 0:
        return {"count": await fastapi_counter.get_counter()}
    else:
        return {"count": await fastapi_counter.increment_counter()}


@app.put("/counter/")
async def update_counter() -> Counter:
    newCount = await fastapi_counter.increment_counter()
    await fastapi_counter.publish_counter(newCount)
    return Counter(count=newCount)


user_chat_room = {
    "user_1": ["chat_room_1", "chat_room_2"],
    "user_2": ["chat_room_3", "chat_room_4"],
}


@app.post("/sse/")
async def sse_counter(request: Request):
    try:
        user_id = request.headers.get("user_id")
        assert user_id is not None, "User ID is required"
        chat_room_ids = user_chat_room[user_id]
        assert chat_room_ids is not None, "Chat room IDs are required"
        pubsub = await redis_message_channel_client.subscribe_to_chat_room(
            chat_room_ids
        )

        queue = asyncio.Queue()

        async def redis_listener():
            try:
                async for message in pubsub.listen():
                    print("Redis message received: >>> ", message)
                    if message["type"] == "message":
                        await queue.put(message["data"])
                    if await request.is_disconnected():
                        print("Client disconnected")
                        break
            except asyncio.CancelledError:
                print("Event stream cancelled")
            finally:
                await pubsub.close()

        listener_task = asyncio.create_task(redis_listener())

        async def event_stream():
            try:
                while not await request.is_disconnected():
                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=1)
                        decoded_message = (
                            message.decode()
                            if isinstance(message, bytes)
                            else str(message)
                        )
                        yield f"data: {decoded_message}\n\n"
                    except asyncio.TimeoutError:
                        continue
            finally:
                listener_task.cancel()
                await listener_task

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        print(f"Error in SSE counter: {e}")
        raise
