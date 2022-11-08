import uuid

from starlette.testclient import TestClient

from examples.redis.main import app


def test_cacheable():
    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable", params={"id": _id})
        last_result = response.json()["result"]
        response = client.get("/cacheable", params={"id": _id})
        current_result = response.json()["result"]
        assert (
            last_result == current_result
        ), f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_with_condition():
    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": False})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": False})
        current_result = response.json()["result"]
        assert (
            last_result != current_result
        ), f"last_result: {last_result}, current_result: {current_result}"

        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": True})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_condition", params={"id": _id, "cache": True})
        current_result = response.json()["result"]
        assert (
            last_result == current_result
        ), f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_with_unless():
    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": False})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": False})
        current_result = response.json()["result"]
        assert (
            last_result.startswith("no") and last_result != current_result
        ), f"last_result: {last_result}, current_result: {current_result}"

        _id = str(uuid.uuid4())
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": True})
        last_result = response.json()["result"]
        response = client.get("/cacheable_with_unless", params={"id": _id, "cache": True})
        current_result = response.json()["result"]
        assert (
            last_result == current_result
        ), f"last_result: {last_result}, current_result: {current_result}"


def test_cacheable_for_get_dict():
    with TestClient(app) as client:
        _id = str(uuid.uuid4())
        response = client.get("/cacheable_for_get_dict", params={"id": _id})
        last_result = response.json()["result"]
        response = client.get("/cacheable_for_get_dict", params={"id": _id})
        current_result = response.json()["result"]
        assert (
            last_result == current_result
        ), f"last_result: {last_result}, current_result: {current_result}"
