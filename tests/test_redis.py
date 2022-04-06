import time
from datetime import datetime

import aioredis
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.decorator import cache
from pytest import fixture

### Constants ###

redis_url = "redis://localhost:6379"

### Fixtures ###

@fixture(scope="session")
def testclient() -> TestClient:
    app = FastAPI()

    @app.get("/clear")
    async def clear():
        return await FastAPICache.clear(namespace="test")

    @app.get("/datetime")
    @cache(namespace="test", expire=2)
    async def get_datetime(request: Request, response: Response):
        return datetime.now().strftime("%Y-%m-%dT%H:%M:%S") # Otherwise returns tz sometimes

    @app.on_event("startup")
    async def startup():
        redis = aioredis.from_url(url=redis_url)
        FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")

    with TestClient(app) as client:
        yield client

### Tests ###

def test_wait_til_expires(testclient: TestClient):
    first_datetime = testclient.get("/datetime").text
    time.sleep(1)
    second_datetime = testclient.get("/datetime").text
    time.sleep(1)
    third_datetime = testclient.get("/datetime").text
    time.sleep(1)
    fourth_datetime = testclient.get("/datetime").text
    assert first_datetime  == second_datetime
    assert second_datetime != third_datetime
    assert third_datetime  == fourth_datetime

def test_set_then_clear(testclient: TestClient):
    first_datetime = testclient.get("/datetime").text
    testclient.get("/clear")
    second_datetime = testclient.get("/datetime").text
    time.sleep(1)
    third_datetime = testclient.get("/datetime").text
    testclient.get("/clear")
    fourth_datetime = testclient.get("/datetime").text
    assert first_datetime  != second_datetime
    assert second_datetime == third_datetime
    assert fourth_datetime != third_datetime
