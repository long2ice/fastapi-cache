from unittest import mock

import httpx
import pytest
from fastapi import FastAPI

from fastapi_cache import FastAPICache


@pytest.fixture
def app():
    return FastAPI()


@pytest.fixture
async def http_client(app: FastAPI):
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def disable_cache():
    with mock.patch.object(FastAPICache, "_enable", False):
        yield
