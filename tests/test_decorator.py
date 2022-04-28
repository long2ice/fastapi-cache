from unittest.mock import patch, MagicMock

import pytest
from pydantic import BaseModel

from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache


def test_default_key_builder():
    return 1


class MyModel(BaseModel):
    name: str
    age: int


@cache(expire=3600)
async def get_model() -> MyModel:
    return MyModel(name="John", age=30)


async def is_cached(key: str) -> bool:
    backend = FastAPICache.get_backend()
    _, ret = await backend.get_with_ttl(key)
    return ret is not None


@pytest.mark.asyncio
async def test_get_model_returns_a_model():

    key_builder = FastAPICache.get_key_builder()
    cache_key = key_builder(get_model, "", args=(), kwargs={})

    # Ensuring the cache key is not cached
    assert not await is_cached(cache_key)

    # First time, when is not cached, will return whatever the function returns
    ret = await get_model()
    assert isinstance(ret, MyModel)

    # Ensuring the cache key is cached
    assert await is_cached(cache_key)

    # Second time, when is cached, will return the cached value, parsing it to a model
    ret = await get_model()
    assert isinstance(ret, MyModel)


