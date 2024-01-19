import time
from typing import Generator
import logging

import pendulum
import pytest
from starlette.testclient import TestClient

from examples.in_memory.main import app
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend


@pytest.fixture(autouse=True)
def init_cache() -> Generator:
    FastAPICache.init(InMemoryBackend())
    yield
    FastAPICache.reset()


def test_datetime() -> None:
    with TestClient(app) as client:
        response = client.get("/datetime")
        now = response.json().get("now")
        now_ = pendulum.now().replace(microsecond=0)
        assert pendulum.parse(now).replace(microsecond=0) == now_
        response = client.get("/datetime")
        now = response.json().get("now")
        assert pendulum.parse(now).replace(microsecond=0) == now_
        time.sleep(3)
        response = client.get("/datetime")
        now = response.json().get("now")
        now = pendulum.parse(now).replace(microsecond=0)
        assert now != now_
        assert now == pendulum.now().replace(microsecond=0)


def test_date() -> None:
    """Test path function without request or response arguments."""
    with TestClient(app) as client:
        response = client.get("/date")
        assert pendulum.parse(response.json()) == pendulum.today()

        # do it again to test cache
        response = client.get("/date")
        assert pendulum.parse(response.json()) == pendulum.today()

        # now test with cache disabled, as that's a separate code path
        FastAPICache._enable = False
        response = client.get("/date")
        assert pendulum.parse(response.json()) == pendulum.today()
        FastAPICache._enable = True


def test_sync() -> None:
    """Ensure that sync function support works."""
    with TestClient(app) as client:
        response = client.get("/sync-me")
        assert response.json() == 42


def test_cache_response_obj() -> None:
    with TestClient(app) as client:
        cache_response = client.get("cache_response_obj")
        assert cache_response.json() == {"a": 1}
        get_cache_response = client.get("cache_response_obj")
        assert get_cache_response.json() == {"a": 1}
        assert get_cache_response.headers.get("cache-control")
        assert get_cache_response.headers.get("etag")


def test_kwargs() -> None:
    with TestClient(app) as client:
        name = "Jon"
        response = client.get("/kwargs", params={"name": name})
        assert response.json() == {"name": name}


def test_cache_control_no_store() -> None:
    with TestClient(app) as client:
        # Cache-Control: no-store should return a fresh result that is not stored,
        # so two hits within the cache TTL should be different, and then
        # removing the removing the header should also not have stored anything.

        # First ensure the cache has expired
        time.sleep(3)

        response = client.get("/datetime", headers={"cache-control": "no-store"})
        response_time_1 = response.json().get("now")
        time.sleep(1)
        response = client.get("/datetime", headers={"cache-control": "no-store"})
        response_time_2 = response.json().get("now")
        assert response_time_1 != response_time_2
        response = client.get("/datetime")

        # now even if we remove the header, we should still get a fresh
        # result because nothing was stored
        response_time_3 = response.json().get("now")
        actual_time = pendulum.now().replace(microsecond=0)
        assert pendulum.parse(response_time_3).replace(microsecond=0) == actual_time
        assert response.headers.get("X-Cache-Hit") != "True"


def test_cache_control_no_cache() -> None:
    with TestClient(app) as client:
        # Cache-Control: no-cache should force a fresh result to be returned
        # AND stored

        response = client.get("/datetime")
        cached_time = response.json().get("now")
        time.sleep(1)
        response = client.get("/datetime")
        response_time = response.json().get("now")
        assert response_time == cached_time
        assert response.headers.get("X-Cache-Hit") == "True"

        response = client.get("/datetime", headers={"cache-control": "no-cache"})
        response_time = response.json().get("now")
        assert response_time != cached_time
        assert response.headers.get("X-Cache-Hit") != "True"
        new_cache_time = response_time

        time.sleep(1)
        response = client.get("/datetime")
        response_time = response.json().get("now")
        assert response_time == new_cache_time
        assert response.headers.get("X-Cache-Hit") == "True"
        cache_ttl = response.headers.get("X-Cache-TTL")
        time.sleep(1)
        response = client.get("/datetime")
        assert cache_ttl != response.headers.get("X-Cache-TTL")


def test_cache_control_etag() -> None:
    with TestClient(app) as client:
        # if-none-match is a header used for validating the cache exists;
        # If present, a GET request should return 304 for a cache hit

        response = client.get("/datetime")
        etag = response.headers.get("etag")

        response = client.get("/datetime", headers={"if-none-match": etag})
        assert response.status_code == 304

        etag = "foo"
        response = client.get("/datetime", headers={"if-none-match": etag})
        assert response.status_code == 200


def test_client_caching() -> None:
    with TestClient(app) as client:
        # Cache-Control: no-store should be returned from this endpoint
        response = client.get("/client-side-cacheable")
        assert response.headers.get("cache-control") != "no-store"
        assert "max-age" in response.headers.get("cache-control")

        response = client.get("/datetime")
        assert response.headers.get("cache-control") == "no-store"
