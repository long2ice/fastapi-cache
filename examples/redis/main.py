from datetime import date, datetime
import time

import redis.asyncio as redis
import uvicorn
from fastapi import FastAPI
from redis.asyncio.connection import ConnectionPool
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

app = FastAPI()

ret = 0


@cache(namespace="test", expire=1)
async def get_ret():
    global ret
    ret = ret + 1
    return ret


@app.get("/")
@cache(namespace="test", expire=20)
async def index(request: Request, response: Response):
    return dict(ret=await get_ret())


@app.get("/clear")
async def clear():
    return await FastAPICache.clear(namespace="test")


@app.get("/date")
@cache(namespace="test", expire=20)
async def get_data(request: Request, response: Response):
    return date.today()


@app.get("/blocking")
@cache(namespace="test", expire=20)
def blocking(request: Request, response: Response):
    time.sleep(5)
    return dict(ret=get_ret())


@app.get("/datetime")
@cache(namespace="test", expire=20)
async def get_datetime(request: Request, response: Response):
    return datetime.now()


@app.on_event("startup")
async def startup():
    pool = ConnectionPool.from_url(url="redis://localhost")
    r = redis.Redis(connection_pool=pool)
    FastAPICache.init(RedisBackend(r), prefix="fastapi-cache")


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
