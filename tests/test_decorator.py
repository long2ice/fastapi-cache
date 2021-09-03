import pytest
import fakeredis.aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from fastapi import FastAPI
from httpx import AsyncClient

app = FastAPI()

# Create dummy aioredis instance for testing
fake_redis = fakeredis.aioredis.FakeRedis()

# Initiate FastAPICache with dummy aioredis instance
FastAPICache.init(RedisBackend(fake_redis), prefix="fastapi-cache")

# Create example custom key builder
def example_key_builder(func, *args, **kwarg):
    return "my-custom-cache-key"

# Create example route with cache decorator, including custom key builder
@app.get("/")
@cache(key_builder=example_key_builder)
async def example():
    return 1

# Asynchronous test
@pytest.mark.asyncio
async def test_custom_key_builder_redis():
    """
    Tests if custom_key_builder creates key value in Redis
    """

    # Call "/" route and await response 
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    # Check if key exists in Redis instance
    key_exists = await fake_redis.exists("my-custom-cache-key")
    assert key_exists

def test_default_key_builder():
    return 1
