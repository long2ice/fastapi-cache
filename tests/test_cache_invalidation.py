from collections import defaultdict
from typing import Any, Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend


@pytest.fixture(autouse=True)
def _init_cache() -> Generator[Any, Any, None]:  # pyright: ignore[reportUnusedFunction]
    FastAPICache.init(InMemoryBackend())
    yield
    FastAPICache.reset()


@pytest.fixture()
def test_client():
    from examples.in_memory.main import app

    with TestClient(app=app) as client:
        yield client


@pytest.fixture(autouse=True)
def set_initial_value_for_files():
    files = defaultdict(
        list,
        {
            1: [1, 2, 3],
            2: [4, 5, 6],
            3: [100],
        },
    )
    with patch("examples.in_memory.main.files", files):
        yield


class TestCacheInvalidation:
    def test_cache_invalidation(self, test_client) -> None:
        response = test_client.get("/files")

        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == [
            {'id': 1, 'value': [1, 2, 3]},
            {'id': 2, 'value': [4, 5, 6]},
            {'id': 3, 'value': [100]},
        ]

        response = test_client.get("/files")

        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        assert response.json() == [
            {'id': 1, 'value': [1, 2, 3]},
            {'id': 2, 'value': [4, 5, 6]},
            {'id': 3, 'value': [100]},
        ]

        # changing file and invalidating first request
        change_response = test_client.patch("/files/1", json={"items": [42]})
        assert change_response.status_code == 200, change_response.json()
        assert change_response.json() == {
            "id": 1,
            "value": [42],
        }

        # this was invalidated
        response = test_client.get("/files")
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == [
            {'id': 1, 'value': [42]},
            {'id': 2, 'value': [4, 5, 6]},
            {'id': 3, 'value': [100]},
        ]

    def test_partial_invalidation(self, test_client) -> None:
        response = test_client.get("/files", params={"file_id_in": [1, 2]})

        assert response.json() == [
            {'id': 1, 'value': [1, 2, 3]},
            {'id': 2, 'value': [4, 5, 6]},
        ]

        response = test_client.get("/files", params={"file_id_in": [2, 3]})

        assert response.json() == [
            {'id': 2, 'value': [4, 5, 6]},
            {'id': 3, 'value': [100]},
        ]

        # changing file with id 1 not causing second request invalidation
        change_response = test_client.patch("/files/1", json={"items": [42]})

        # this was invalidated
        response = test_client.get("/files", params={"file_id_in": [1, 2]})
        assert response.headers.get("X-FastAPI-Cache") == "MISS"
        assert response.json() == [
            {'id': 1, 'value': [42]},
            {'id': 2, 'value': [4, 5, 6]},
        ]

        # this is not
        response = test_client.get("/files", params={"file_id_in": [2, 3]})
        assert response.headers.get("X-FastAPI-Cache") == "HIT"
        assert response.json() == [
            {'id': 2, 'value': [4, 5, 6]},
            {'id': 3, 'value': [100]},
        ]
