# fastapi-cache

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


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

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
injected_dependency_namespace | prefix for injected dependency keywords, defaults to `__fastapi_cache`.
cache_status_header | Name for the header on the response indicating if the request was served from cache; either `HIT` or `MISS`. Defaults to `X-FastAPI-Cache`.

You can also use `cache` as decorator like other cache tools to cache common function result.

### Injected Request and Response dependencies

The `cache` decorator adds dependencies for the `Request` and `Response` objects, so that it can
add cache control headers to the outgoing response, and return a 304 Not Modified response when
the incoming request has a matching If-Non-Match header. This only happens if the decorated
endpoint doesn't already list these objects directly.

The keyword arguments for these extra dependencies are named
`__fastapi_cache_request` and `__fastapi_cache_response` to minimize collisions.
Use the `injected_dependency_namespace` argument to `@cache()` to change the
prefix used if those names would clash anyway.


### Supported data types

When using the (default) `JsonCoder`, the cache can store any data type that FastAPI can convert to JSON, including Pydantic models and dataclasses,
_provided_ that your endpoint has a correct return type annotation, unless
the return type is a standard JSON-supported type such as a dictionary or a list.

E.g. for an endpoint that returns a Pydantic model named `SomeModel`:

```python
from .models import SomeModel, create_some_model

@app.get("/foo")
@cache(expire=60)
async def foo() -> SomeModel:
    return create_some_model
```

It is not sufficient to configure a response model in the route decorator; the cache needs to know what the method itself returns.

If no return type decorator is given, the primitive JSON type is returned instead.

For broader type support, use the `fastapi_cache.coder.PickleCoder` or implement a custom coder (see below).

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
        namespace: str = "",
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


### RedisBackend

When using the redis backend, please make sure you pass in a redis client that does [_not_ decode responses][redis-decode] (`decode_responses` **must** be `False`, which is the default). Cached data is stored as `bytes` (binary), decoding these i the redis client would break caching.

[redis-decode]: https://redis-py.readthedocs.io/en/latest/examples/connection_examples.html#by-default-Redis-return-binary-responses,-to-decode-them-use-decode_responses=True

## Tests and coverage

```shell
coverage run -m pytest
coverage html
xdg-open htmlcov/index.html
```

## License

This project is licensed under the [Apache-2.0](https://github.com/long2ice/fastapi-cache/blob/master/LICENSE) License.
