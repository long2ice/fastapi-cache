import pendulum
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from examples.crud import crud_example
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
async def get_date():
    return pendulum.today()


@app.get("/datetime")
@cache(namespace="test", expire=2)
async def get_datetime(request: Request, response: Response):
    return {"now": pendulum.now()}


@app.get("/sync-me")
@cache(namespace="test")
def sync_me():
    # as per the fastapi docs, this sync function is wrapped in a thread,
    # thereby converted to async. fastapi-cache does the same.
    return 42


@app.get("/cacheable")
async def cacheable(id: str):
    result = await crud_example.get(_id=id)
    return {"result": result}


@app.get("/cacheable_for_get_dict")
async def cacheable_for_get_dict(id: str):
    result = await crud_example.get_dict(_id=id)
    return {"result": result}


@app.get("/cacheable_with_condition")
async def cacheable_with_condition(id: str, cache: bool):
    result = await crud_example.get_with_condition(_id=id, is_cache=cache)
    return {"result": result}


@app.get("/cacheable_with_unless")
async def cacheable_with_unless(id: str, cache: bool):
    result = await crud_example.get_with_unless(_id=id, is_cache=cache)
    return {"result": result}


@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())


if __name__ == "__main__":
    uvicorn.run("main:app", debug=True, reload=True)
