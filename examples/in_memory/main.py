from datetime import date, datetime

import uvicorn
from fastapi import FastAPI, Depends

from fastapi_cache import FastAPICache, cache_ctx
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache


app = FastAPI(dependencies=[Depends(cache_ctx)])

ret = 0


@cache(namespace="test", expire=1)
async def get_ret():
    global ret
    ret = ret + 1
    return ret


@app.get("/")
@cache(namespace="test", expire=20)
async def index():
    return dict(ret=await get_ret())


@app.get("/clear")
async def clear():
    return await FastAPICache.clear(namespace="test")


@app.get("/date")
@cache(namespace="test", expire=20)
async def get_data():
    return date.today()


@app.get("/datetime")
@cache(namespace="test", expire=20)
async def get_datetime():
    return datetime.now()


@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
