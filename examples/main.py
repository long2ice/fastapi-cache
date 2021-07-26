import aioredis
import uvicorn
from fastapi import FastAPI
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


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(url="redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
