import pytest

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend


@pytest.fixture(autouse=True)
def setup():
    FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache-test")
