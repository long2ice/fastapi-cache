import pendulum
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

app = FastAPI()

ret = 0


@cache(namespace="test", expire=1)
async def get_ret():
    global ret
    ret = ret + 1
    return ret


@app.get("/")
@cache(namespace="test", expire=10)
async def index():
    return dict(ret=await get_ret())


@app.get("/clear")
async def clear():
    return await FastAPICache.clear(namespace="test")


@app.get("/date")
@cache(namespace="test", expire=10)
async def get_data():
    return pendulum.today()


@app.get("/datetime")
@cache(namespace="test", expire=2)
async def get_datetime(request: Request, response: Response):
    return {"now": pendulum.now()}


@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
