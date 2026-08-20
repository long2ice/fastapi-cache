import asyncio
import time
from typing import Any, Dict, Generator, List, Tuple

import pendulum
import pytest
from starlette.testclient import TestClient

from examples.in_memory.main import app
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache


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
        now_ = pendulum.now().replace(microsecond=0)
        assert pendulum.parse(now).replace(microsecond=0) == now_
        response = client.get("/datetime")
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        now = response.json().get("now")
        assert pendulum.parse(now).replace(microsecond=0) == now_
        time.sleep(3)
        response = client.get("/datetime")
        now = response.json().get("now")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        now = pendulum.parse(now).replace(microsecond=0)
        assert now != now_
        assert now == pendulum.now().replace(microsecond=0)


def test_date() -> None:
    """Test path function without request or response arguments."""
    with TestClient(app) as client:
        response = client.get("/date")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert pendulum.parse(response.json()) == pendulum.today()

        # do it again to test cache
        response = client.get("/date")
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        assert pendulum.parse(response.json()) == pendulum.today()

        # now test with cache disabled, as that's a separate code path
        FastAPICache._enable = False  # pyright: ignore[reportPrivateUsage]
        response = client.get("/date")
        assert "X-FastAPI-Cache" not in response.headers
        assert pendulum.parse(response.json()) == pendulum.today()
        FastAPICache._enable = True # pyright: ignore[reportPrivateUsage]


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

def test_cache_control() -> None:
    with TestClient(app) as client:
        response = client.get("/cached_put")
        assert response.json() == {"value": 1}

        # HIT
        response = client.get("/cached_put")
        assert response.json() == {"value": 1}

        # no-cache
        response = client.get("/cached_put", headers={"Cache-Control": "no-cache"})
        assert response.json() == {"value": 2}

        response = client.get("/cached_put")
        assert response.json() == {"value": 2}

        # no-store
        response = client.get("/cached_put", headers={"Cache-Control": "no-store"})
        assert response.json() == {"value": 3}

        response = client.get("/cached_put")
        assert response.json() == {"value": 2}


def test_exclude_params() -> None:
    """Parameters listed in exclude_params are left out of the cache key."""
    with TestClient(app) as client:
        response = client.get("/excluded_params", params={"name": "Jon", "nonce": "a"})
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == {"name": "Jon", "nonce": "a", "value": 1}

        # a different nonce hits the same cache entry
        response = client.get("/excluded_params", params={"name": "Jon", "nonce": "b"})
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        assert response.json() == {"name": "Jon", "nonce": "a", "value": 1}

        # a different name is still a distinct entry
        response = client.get("/excluded_params", params={"name": "Ben", "nonce": "b"})
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == {"name": "Ben", "nonce": "b", "value": 2}


def test_exclude_params_positional() -> None:
    """Positional arguments are matched to their parameter name by position."""
    calls: List[Tuple[int, int]] = []

    @cache(namespace="test", expire=5, exclude_params=["b"])
    async def func(a: int, b: int) -> int:
        calls.append((a, b))
        return a

    assert asyncio.run(func(1, 2)) == 1
    assert asyncio.run(func(1, 3)) == 1
    assert calls == [(1, 2)]

    assert asyncio.run(func(4, 3)) == 4
    assert calls == [(1, 2), (4, 3)]


def test_exclude_params_unknown_name() -> None:
    """A typo in exclude_params is reported when the function is decorated."""
    with pytest.raises(ValueError, match="nonexistent"):

        @cache(namespace="test", exclude_params=["nonexistent"])
        async def func(a: int) -> int:
            return a


def test_exclude_params_var_keyword() -> None:
    """Functions taking **kwargs accept any excluded name."""

    @cache(namespace="test", expire=5, exclude_params=["nonce"])
    async def func(**kwargs: Any) -> Dict[str, Any]:
        return kwargs

    assert asyncio.run(func(name="Jon", nonce="a")) == {"name": "Jon", "nonce": "a"}
    assert asyncio.run(func(name="Jon", nonce="b")) == {"name": "Jon", "nonce": "a"}
