import pytest
import fakeredis.aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from unittest.mock import patch
from fastapi import FastAPI
from httpx import AsyncClient

app = FastAPI()

# Create dummy aioredis instance for testing
fake_redis = fakeredis.aioredis.FakeRedis()

# Initiate FastAPICache with dummy aioredis instance
FastAPICache.init(RedisBackend(fake_redis), prefix="fastapi-cache")

# Create example route with cache decorator
@app.get("/")
@cache()
async def example():
    return 1

# Create example function for on_new_key
def on_new_key(func, *args, **kwargs):
    return None

# Create example function for on_existing_key
def on_existing_key(func, *args, **kwargs):
    return None

# Asynchronous test
@pytest.mark.asyncio
@patch("tests.test_handlers.on_existing_key")
@patch("tests.test_handlers.on_new_key")
# Patches are applied bottom up - https://docs.python.org/3/library/unittest.mock.html#quick-guide
async def test_event_handlers_triggered(mock_new_key_function, mock_existing_key_function):
    """
    Tests if event handler functions are triggered at the correct part of the caching lifecycle
    """
    # Clear the cache
    FastAPICache.clear

    # Set functions for new and existing key
    FastAPICache.set_on_new_key(mock_new_key_function)
    FastAPICache.set_on_existing_key(mock_existing_key_function)

    # Call "/"" route and await response. Creating a new key
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    # Check new key function called
    mock_new_key_function.assert_called()
    # Check existing key function not called
    mock_existing_key_function.assert_not_called()

    # Reset mock for new key function
    mock_new_key_function.reset_mock()

    # Call "/"" route and await response. Key already exists
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/")

    # Check existing key function called
    mock_existing_key_function.assert_called()
    # Check new key function not called
    mock_new_key_function.assert_not_called()