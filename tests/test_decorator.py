import time

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
