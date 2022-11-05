import time
import uuid

import pendulum
from fastapi_cache import FastAPICache
from starlette.testclient import TestClient

from examples.in_memory.main import app


def test_datetime():
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

def test_date():
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

def test_sync():
    """Ensure that sync function support works."""
    with TestClient(app) as client:
        response = client.get("/sync-me")
        assert response.json() == 42


def test_cacheable():
    from examples.redis.main import app

    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable", params={"id": _id})
        last_result = response.json()["result"]
        response = client.get("/cacheable", params={"id": _id})
        current_result = response.json()["result"]
        assert last_result == current_result, f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_with_condition():
    from examples.redis.main import app

    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": False})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": False})
        current_result = response.json()["result"]
        assert last_result != current_result, f"last_result: {last_result}, current_result: {current_result}"

        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": True})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": True})
        current_result = response.json()["result"]
        assert last_result == current_result, f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_with_unless():
    from examples.redis.main import app

    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": False})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": False})
        current_result = response.json()["result"]
        assert last_result.startswith("no") and last_result != current_result, f"last_result: {last_result}, current_result: {current_result}"

        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": True})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": True})
        current_result = response.json()["result"]
        assert last_result == current_result, f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_for_get_dict():
    from examples.redis.main import app

    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_for_get_dict", params={"id": _id})
        last_result = response.json()["result"]
        response = client.get("/cacheable_for_get_dict", params={"id": _id})
        current_result = response.json()["result"]
        assert last_result == current_result, f"last_result: {last_result}, current_result: {current_result}"
