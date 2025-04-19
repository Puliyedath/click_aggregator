import time
from typing import Union
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.redis_client import CounterRedisClient
import os
import signal
import sys
from contextlib import asynccontextmanager

fastapi_counter = CounterRedisClient(
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


@app.get("/")
def read_root():
    return {"message": "Hello Counter app"}


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


@app.get("/sse")
async def sse_counter(request: Request):
    return StreamingResponse(
        fastapi_counter.async_counter_reader(request), media_type="text/event-stream"
    )
