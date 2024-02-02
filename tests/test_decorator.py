import time
from typing import Any, Generator

import pendulum
import pytest
from starlette.testclient import TestClient

from examples.in_memory.main import app
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend


@pytest.fixture(autouse=True)
def _init_cache() -> Generator[Any, Any, None]:  # pyright: ignore[reportUnusedFunction]
    FastAPICache.init(InMemoryBackend())
    yield
    FastAPICache.reset()


def test_datetime() -> None:
    with TestClient(app) as client:
        response = client.get("/datetime")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        now = response.json().get("now")
        now_ = pendulum.now().replace(microsecond=0)  # type: ignore[no-untyped-call]
        assert pendulum.parse(now).replace(microsecond=0) == now_  # type: ignore[attr-defined]
        response = client.get("/datetime")
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        now = response.json().get("now")
        assert pendulum.parse(now).replace(microsecond=0) == now_  # type: ignore[attr-defined]
        time.sleep(3)
        response = client.get("/datetime")
        now = response.json().get("now")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        now = pendulum.parse(now).replace(microsecond=0)  # type: ignore[attr-defined]
        assert now != now_
        assert now == pendulum.now().replace(microsecond=0)  # type: ignore[no-untyped-call]


def test_date() -> None:
    """Test path function without request or response arguments."""
    with TestClient(app) as client:
        response = client.get("/date")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert pendulum.parse(response.json()) == pendulum.today()  # type: ignore[attr-defined]

        # do it again to test cache
        response = client.get("/date")
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        assert pendulum.parse(response.json()) == pendulum.today()  # type: ignore[attr-defined]

        # now test with cache disabled, as that's a separate code path
        FastAPICache._enable = False  # pyright: ignore[reportPrivateUsage]
        response = client.get("/date")
        assert "X-FastAPI-Cache" not in response.headers
        assert pendulum.parse(response.json()) == pendulum.today()  # type: ignore[attr-defined]
        FastAPICache._enable = True  # pyright: ignore[reportPrivateUsage]


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
        assert "X-FastAPI-Cache" not in response.headers
        assert response.json() == {"name": name}


def test_method() -> None:
    with TestClient(app) as client:
        response = client.get("/method")
        assert response.json() == 17


def test_pydantic_model() -> None:
    with TestClient(app) as client:
        r1 = client.get("/pydantic_instance")
        assert r1.headers.get("X-FastAPI-Cache") == "MISS"
        r2 = client.get("/pydantic_instance")
        assert r2.headers.get("X-FastAPI-Cache") == "HIT"
        assert r1.json() == r2.json()


def test_non_get() -> None:
    with TestClient(app) as client:
        response = client.put("/uncached_put")
        assert "X-FastAPI-Cache" not in response.headers
        assert response.json() == {"value": 1}
        response = client.put("/uncached_put")
        assert "X-FastAPI-Cache" not in response.headers
        assert response.json() == {"value": 2}


def test_alternate_injected_namespace() -> None:
    with TestClient(app) as client:
        response = client.get("/namespaced_injection")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == {"__fastapi_cache_request": 42, "__fastapi_cache_response": 17}
