# fastapi-cache - fork for Playfully

![pypi](https://img.shields.io/pypi/v/fastapi-cache2.svg?style=flat)
![license](https://img.shields.io/github/license/long2ice/fastapi-cache)
![workflows](https://github.com/long2ice/fastapi-cache/workflows/pypi/badge.svg)
![workflows](https://github.com/long2ice/fastapi-cache/workflows/ci/badge.svg)

## Introduction

`fastapi-cache` is a tool to cache fastapi response and function result, with backends support `redis`, `memcache`,
and `dynamodb`.

## Features

- Support `redis`, `memcache`, `dynamodb`, and `in-memory` backends.
- Easily integration with `fastapi`.
- Support http cache like `ETag` and `Cache-Control`.

## Requirements

- `asyncio` environment.
- `redis` if use `RedisBackend`.
- `memcache` if use `MemcacheBackend`.
- `aiobotocore` if use `DynamoBackend`.

## Install

```shell
> pip install fastapi-cache2
```

or

```shell
> pip install "fastapi-cache2[redis]"
```

## Testing
This PR also adds new unit tests to verify the logic

```shell
> pytest -v
```

## Usage

### Quick Start

```python
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis

app = FastAPI()


@cache()
async def get_cache():
    return 1


@app.get("/")
@cache(expire=60)
async def index():
    return dict(hello="world")

@asynccontextmanager
async def lifespan(_: FastAPI):
    """Lifespan for managing Redis cache and other startup activities"""
    # Load the Redis Cache
    redis = aioredis.from_url(
        settings.redis_endpoint,
        username="default",
        password=settings.get_secret("redis_default_password"),
    )
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache", enable=enable)
    yield
    FastAPICache.reset()
```

### Initialization

Firstly you must call `FastAPICache.init` on startup event of `fastapi`, there are some global config you can pass in.

### Use `cache` decorator

If you want cache `fastapi` response transparently, you can use `cache` as decorator between router decorator and view
function and must pass `request` as param of view function.

Parameter | type, description
------------ | -------------
expire | int, states a caching time in seconds
namespace | str, namespace to use to store certain cache items
coder | which coder to use, e.g. JsonCoder
key_builder | which key builder to use, default to builtin
allow_client_caching | the `response` should allow the caller to cache (default to False)

You can also use `cache` as decorator like other cache tools to cache common function result.

### Custom coder

By default use `JsonCoder`, you can write custom coder to encode and decode cache result, just need
inherit `fastapi_cache.coder.Coder`.

```python
@app.get("/")
@cache(expire=60, coder=JsonCoder)
async def index():
    return dict(hello="world")
```

### Custom key builder

By default use builtin key builder, if you need, you can override this and pass in `cache` or `FastAPICache.init` to
take effect globally.


```python
def my_key_builder(
        func,
        namespace: Optional[str] = "",
        request: Request = None,
        response: Response = None,
        *args,
        **kwargs,
):
    prefix = FastAPICache.get_prefix()
    cache_key = f"{prefix}:{namespace}:{func.__module__}:{func.__name__}:{args}:{kwargs}"
    return cache_key


@app.get("/")
@cache(expire=60, coder=JsonCoder, key_builder=my_key_builder)
async def index():
    return dict(hello="world")
```

### InMemoryBackend

`InMemoryBackend` store cache data in memory and use lazy delete, which mean if you don't access it after cached, it
will not delete automatically.

### Allow-Client-Caching
For certain content, we want to handle all caching at the server (e.g. so we can do automatic
invalidation, e.g. when the user profile changes so cached shortlists are no longer valid)
so this flag instructs the client (i.e. Browser/app) not to do any local caching. If content is
relatively stable, it can be overridden with the `allow_client_caching` parameter inside the `@cache()`
decorator.

## Headers

### Cache-Control (Request)
The `Cache-Control` header can be used in a GET Request to control the behavior of the cache:

* If `Cache-Control: no-store` is set on the request, then FastAPI-Cache will return a fresh result
  and will not store that result. However, an existing cache will not be removed, so the next request
  may still return the cached result.
* If `Cache-Control: no-cache` is set on the request, then FastAPI-Cache will generate a fresh result
  and will store that result (overwriting the cache if necessary)
* These two headers are mutually exclusive

### if-none-match (Request)
If the `if-none-match` header is set on the request, then FastAPI-Cache will return an `HTTP_304: Not Modified`
response if a cached result is found and its `ETag` value matches the `ETag` header.

### Cache-Control (Response)
Because we want to handle cache invalidation with server-side logic, by default the response will
return `Cache-Control: no-store` indicating that the client should always check the server for fresh
results.

If 'allow_client_caching' is set, the `Cache-Control: max-age=####` header will be returned instead.


### X-Cache-Hit (Response)
FastAPI-Cache will return a `X-Cache-Hit: True` header if the response is served from the cache

### X-Cache-TTL (Response)
If the server cache was hit, `X-Cache-TTL` will contain the (approx) remaining TTL for the cache

### ETag (Response)
FastAPI-Cache will return an `ETag` header if the result can be cached by the caller


## Tests and coverage

```shell
coverage run -m pytest
coverage html
xdg-open htmlcov/index.html
```

## License

This project is licensed under the [Apache-2.0](https://github.com/long2ice/fastapi-cache/blob/master/LICENSE) License.
