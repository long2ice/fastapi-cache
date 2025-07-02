# pyright: reportGeneralTypeIssues=false
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator, Dict, List, Optional

import pendulum
import uvicorn
from fastapi import Body, FastAPI, Query
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache, cache_invalidator
from fastapi_cache.tag_provider import TagProvider
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


app = FastAPI(lifespan=lifespan)

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
@cache(namespace="test")  # pyright: ignore[reportArgumentType]
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


put_ret2 = 0


@app.get("/cached_put")
@cache(namespace="test", expire=5)
async def cached_put():
    global put_ret2
    put_ret2 = put_ret2 + 1
    return {"value": put_ret2}


@app.get("/namespaced_injection")
@cache(namespace="test", expire=5, injected_dependency_namespace="monty_python")  # pyright: ignore[reportArgumentType]
def namespaced_injection(
    __fastapi_cache_request: int = 42, __fastapi_cache_response: int = 17
) -> Dict[str, int]:
    return {
        "__fastapi_cache_request": __fastapi_cache_request,
        "__fastapi_cache_response": __fastapi_cache_response,
    }


# Note: examples with cache invalidation
files = defaultdict(
    list,
    {
        1: [1, 2, 3],
        2: [4, 5, 6],
        3: [100],
    },
)

FileTagProvider = TagProvider("file")


# Note: providing tags for future granular cache invalidation
@app.get("/files")
@cache(expire=10, tag_provider=FileTagProvider)
async def get_files(file_id_in: Annotated[Optional[List[int]], Query()] = None):
    return [
        {"id": k, "value": v}
        for k, v in files.items()
        if (True if not file_id_in else k in file_id_in)
    ]


# Note: here we're retrieving keys by file_id, so we also need to invalidate this, when file changes
@app.get("/files/{file_id:int}")
@cache(
    expire=10,
    tag_provider=FileTagProvider,
    items_provider=lambda data, method_args, method_kwargs: [
        {"id": method_kwargs["file_id"]}
    ],
)
async def get_file_keys(file_id: int):
    if file_id in files:
        return files[file_id]
    return Response("file id not found")


# Note: here we can use default invalidator, because in response we have :id:
@app.patch("/files/{file_id:int}")
@cache_invalidator(tag_provider=FileTagProvider)
async def edit_file(file_id: int, items: Annotated[List[int], Body(embed=True)]):
    files[file_id] = items
    return {
        "id": file_id,
        "value": files[file_id]
    }


# Note: here we need to use custom :invalidator: because we don't have access to identifier in response
@app.delete("/files/{file_id:int}")
@cache_invalidator(
    tag_provider=FileTagProvider, invalidator=lambda resp, kwargs: kwargs["file_id"]
)
async def delete_file(file_id: int):
    if file_id in files:
        del files[file_id]


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
