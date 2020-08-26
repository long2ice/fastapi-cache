# fastapi-cache

![pypi](https://img.shields.io/pypi/v/fastapi-cache2.svg?style=flat)
![license](https://img.shields.io/github/license/long2ice/fastapi-cache)
![workflows](https://github.com/long2ice/fastapi-cache/workflows/pypi/badge.svg)
![workflows](https://github.com/long2ice/fastapi-cache/workflows/ci/badge.svg)

## Introduction

`fastapi-cache` is a tool to cache fastapi response and function result, with backends support `redis` and `memcache`.

## Features

- Support `redis` and `memcache` .
- Easily integration with `fastapi`.
- Support http cache like `ETag` and `Cache-Control`.

## Requirements

- `asyncio` environment.
- `redis` if use `RedisBackend`.
- `memcache` if use `MemcacheBackend`.

## Install

```shell
> pip install fastapi-cache2[redis]
```

or

```shell
> pip install fastapi-cache2[memcache]
```

## Usage

### Quick Start

```python
import aioredis
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache_response, cache

app = FastAPI()


@cache()
async def get_cache():
    return 1


@app.get("/")
@cache_response(expire=60)
async def index(request: Request, response: Response):
    return dict(hello="world")


@app.on_event("startup")
async def startup():
    redis = await aioredis.create_redis_pool("redis://localhost", encoding="utf8")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

```

### Use `cache_response`

If you want cache `fastapi` response transparently, you can use cache_response as decorator between router decorator and view function and must pass `request` as param of view function.

And if you want use `ETag` and `Cache-Control` features, you must pass `response` param also.

### Use `cache`

You can use `cache` as decorator like other cache tools to cache common function result.

## License

This project is licensed under the [Apache-2.0](https://github.com/long2ice/fastapi-cache/blob/master/LICENSE) License.
