# pyright: reportGeneralTypeIssues=false
from typing import Dict, Optional

import pendulum
import uvicorn
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

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
    return {"ret": await get_ret()}


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


@cache(namespace="test")
async def func_kwargs(*unused_args, **kwargs):
    return kwargs


@app.get("/kwargs")
async def get_kwargs(name: str):
    return await func_kwargs(name, name=name)


@app.get("/sync-me")
@cache(namespace="test")
def sync_me():
    # as per the fastapi docs, this sync function is wrapped in a thread,
    # thereby converted to async. fastapi-cache does the same.
    return 42


@app.get("/cache_response_obj")
@cache(namespace="test", expire=5)
async def cache_response_obj():
    return JSONResponse({"a": 1})


class SomeClass:
    def __init__(self, value):
        self.value = value

    async def handler_method(self):
        return self.value


# register an instance method as a handler
instance = SomeClass(17)
app.get("/method")(cache(namespace="test")(instance.handler_method))


# cache a Pydantic model instance; the return type annotation is required in this case
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app.get("/pydantic_instance")
@cache(namespace="test", expire=5)
async def pydantic_instance() -> Item:
    return Item(name="Something", description="An instance of a Pydantic model", price=10.5)


put_ret = 0


@app.put("/uncached_put")
@cache(namespace="test", expire=5)
async def uncached_put():
    global put_ret
    put_ret = put_ret + 1
    return {"value": put_ret}


@app.get("/namespaced_injection")
@cache(namespace="test", expire=5, injected_dependency_namespace="monty_python")
def namespaced_injection(
    __fastapi_cache_request: int = 42, __fastapi_cache_response: int = 17
) -> Dict[str, int]:
    return {
        "__fastapi_cache_request": __fastapi_cache_request,
        "__fastapi_cache_response": __fastapi_cache_response,
    }


@app.on_event("startup")
async def startup():
    FastAPICache.init(InMemoryBackend())


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
