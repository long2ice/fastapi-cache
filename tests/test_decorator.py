import time

import pendulum
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
