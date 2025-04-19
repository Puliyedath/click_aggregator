from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Counter(BaseModel):
    count: int


counter = Counter(count=0)


@app.get("/")
def read_root():
    return {"message": "Hello Counter app"}


@app.get("/counter")
def get_counter():
    return {"count": counter.count}


@app.put("/counter/")
def update_counter():
    counter.count += 1
    return {"count": counter.count}
