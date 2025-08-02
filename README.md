# fastapi-cache

[![pypi](https://img.shields.io/pypi/v/fastapi-cache2.svg?style=flat)](https://pypi.org/p/fastapi-cache2)
[![license](https://img.shields.io/github/license/long2ice/fastapi-cache)](https://github.com/long2ice/fastapi-cache/blob/main/LICENSE)
[![CI/CD](https://github.com/long2ice/fastapi-cache/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/long2ice/fastapi-cache/actions/workflows/ci-cd.yml)

## Introduction

`fastapi-cache` is a tool to cache FastAPI endpoint and function results, with
backends supporting Redis, Memcached, and Amazon DynamoDB.

## Features

- Supports `redis`, `memcache`, `dynamodb`, and `in-memory` backends.
- Easy integration with [FastAPI](https://fastapi.tiangolo.com/).
- Support for HTTP cache headers like `ETag` and `Cache-Control`, as well as conditional `If-Match-None` requests.
- Dogpile prevention (cache stampede mitigation) to prevent multiple simultaneous cache refreshes.

## Requirements

- FastAPI
- `redis` when using `RedisBackend`.
- `memcache` when using `MemcacheBackend`.
- `aiobotocore` when using `DynamoBackend`.

## Install

```shell
> pip install fastapi-cache2
```

or

```shell
> pip install "fastapi-cache2[redis]"
```

or

```shell
> pip install "fastapi-cache2[memcache]"
```

or

```shell
> pip install "fastapi-cache2[dynamodb]"
```

## Usage

### Quick Start

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache

from redis import asyncio as aioredis


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield


app = FastAPI(lifespan=lifespan)


@cache()
async def get_cache():
    return 1


@app.get("/")
@cache(expire=60)
async def index():
    return dict(hello="world")
```

### Initialization

First you must call `FastAPICache.init` during startup FastAPI startup; this is where you set global configuration.

### Use the `@cache` decorator

If you want cache a FastAPI response transparently, you can use the `@cache`
decorator between the router decorator and the view function.

Parameter | type | default | description
------------ | ----| --------- | --------
`expire` | `int` |  | sets the caching time in seconds
`namespace` | `str` | `""` | namespace to use to store certain cache items
`coder` | `Coder` | `JsonCoder` | which coder to use, e.g. `JsonCoder`
`key_builder` | `KeyBuilder` callable | `default_key_builder` | which key builder to use
`injected_dependency_namespace` | `str` | `__fastapi_cache` | prefix for injected dependency keywords.
`cache_status_header` | `str` | `X-FastAPI-Cache` | Name for the header on the response indicating if the request was served from cache; either `HIT` or `MISS`.
`enable_dogpile_prevention` | `bool` | `None` | Enable dogpile prevention (defaults to global setting)
`dogpile_grace_time` | `float` | `None` | Maximum time to wait for another request to complete (defaults to global setting)
`dogpile_wait_time` | `float` | `None` | Time to wait between checks (defaults to global setting)
`dogpile_max_wait_time` | `float` | `None` | Maximum total wait time (defaults to global setting)

You can also use the `@cache` decorator on regular functions to cache their result.

### Dogpile Prevention

`fastapi-cache` includes built-in dogpile prevention (also known as cache stampede prevention) to handle the common scenario where multiple concurrent requests try to refresh an expired cache entry simultaneously.

When dogpile prevention is enabled:
1. The first request to find an expired cache entry will proceed to compute the new value
2. Subsequent requests for the same key will wait briefly for the first request to complete
3. Once the value is computed, all waiting requests will use the newly cached value
4. If the computation takes too long, waiting requests will eventually proceed independently

This prevents overwhelming your backend when popular cache entries expire.

#### Configuring Dogpile Prevention

You can configure dogpile prevention globally when initializing FastAPICache:

```python
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

app = FastAPI()

@app.on_event("startup")
async def startup():
    FastAPICache.init(
        RedisBackend(redis_client),
        prefix="my-app",
        enable_dogpile_prevention=True,  # Enable globally
        dogpile_grace_time=60.0,         # Wait up to 60 seconds for computation
        dogpile_wait_time=0.1,           # Check every 100ms
        dogpile_max_wait_time=5.0,       # Wait maximum 5 seconds
    )
```

Or configure it per endpoint:

```python
@app.get("/expensive-computation")
@cache(
    expire=300,
    enable_dogpile_prevention=True,
    dogpile_grace_time=30.0,  # This endpoint's computation might take up to 30s
)
async def expensive_endpoint():
    # Expensive computation here
    return compute_expensive_result()
```

To disable dogpile prevention for specific endpoints:

```python
@app.get("/fast-endpoint")
@cache(expire=60, enable_dogpile_prevention=False)
async def fast_endpoint():
    return {"data": "fast"}
```

### Injected Request and Response dependencies

The `cache` decorator injects dependencies for the `Request` and `Response`
objects, so that it can add cache control headers to the outgoing response, and
return a 304 Not Modified response when the incoming request has a matching
`If-Non-Match` header. This only happens if the decorated endpoint doesn't already
list these dependencies already.

The keyword arguments for these extra dependencies are named
`__fastapi_cache_request` and `__fastapi_cache_response` to minimize collisions.
Use the `injected_dependency_namespace` argument to `@cache` to change the
prefix used if those names would clash anyway.


### Supported data types

When using the (default) `JsonCoder`, the cache can store any data type that FastAPI can convert to JSON, including Pydantic models and dataclasses,
_provided_ that your endpoint has a correct return type annotation. An
annotation is not needed if the return type is a standard JSON-supported Python
type such as a dictionary or a list.

E.g. for an endpoint that returns a Pydantic model named `SomeModel`, the return annotation is used to ensure that the cached result is converted back to the correct class:

```python
from .models import SomeModel, create_some_model

@app.get("/foo")
@cache(expire=60)
async def foo() -> SomeModel:
    return create_some_model()
```

It is not sufficient to configure a response model in the route decorator; the cache needs to know what the method itself returns. If no return type decorator is given, the primitive JSON type is returned instead.

For broader type support, use the `fastapi_cache.coder.PickleCoder` or implement a custom coder (see below).

### Custom coder

By default use `JsonCoder`, you can write custom coder to encode and decode cache result, just need
inherit `fastapi_cache.coder.Coder`.

```python
from typing import Any
import orjson
from fastapi.encoders import jsonable_encoder
from fastapi_cache import Coder

class ORJsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        return orjson.dumps(
            value,
            default=jsonable_encoder,
            option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY,
        )

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return orjson.loads(value)


@app.get("/")
@cache(expire=60, coder=ORJsonCoder)
async def index():
    return dict(hello="world")
```

### Custom key builder

By default the `default_key_builder` builtin key builder is used; this creates a
cache key from the function module and name, and the positional and keyword
arguments converted to their `repr()` representations, encoded as a MD5 hash.
You can provide your own by passing a key builder in to `@cache()`, or to
`FastAPICache.init()` to apply globally.

For example, if you wanted to use the request method, URL and query string as a cache key instead of the function identifier you could use:

```python
def request_key_builder(
    func,
    namespace: str = "",
    *,
    request: Request = None,
    response: Response = None,
    *args,
    **kwargs,
):
    return ":".join([
        namespace,
        request.method.lower(),
        request.url.path,
        repr(sorted(request.query_params.items()))
    ])


@app.get("/")
@cache(expire=60, key_builder=request_key_builder)
async def index():
    return dict(hello="world")
```

## Backend notes

### InMemoryBackend

The `InMemoryBackend` stores cache data in memory and only deletes when an
expired key is accessed. This means that if you don't access a function after
data has been cached, the data will not be removed automatically.

### RedisBackend

When using the Redis backend, please make sure you pass in a redis client that does [_not_ decode responses][redis-decode] (`decode_responses` **must** be `False`, which is the default). Cached data is stored as `bytes` (binary), decoding these in the Redis client would break caching.

[redis-decode]: https://redis-py.readthedocs.io/en/latest/examples/connection_examples.html#by-default-Redis-return-binary-responses,-to-decode-them-use-decode_responses=True

## Tests and coverage

```shell
coverage run -m pytest
coverage html
xdg-open htmlcov/index.html
```

## License

This project is licensed under the [Apache-2.0](https://github.com/long2ice/fastapi-cache/blob/master/LICENSE) License.

## Sponsor

[![Powered by DartNode](https://dartnode.com/branding/DN-Open-Source-sm.png)](https://dartnode.com "Powered by DartNode - Free VPS for Open Source")