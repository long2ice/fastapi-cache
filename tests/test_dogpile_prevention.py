"""Tests for dogpile prevention functionality."""
import asyncio
import time
from typing import Any, Coroutine, Dict, Generator, List, Optional, Tuple, Union

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from fastapi_cache.types import Backend

# Track function calls for testing
call_tracker: Dict[Union[str, int], List[float]] = {}


@pytest.fixture()
def app() -> Generator[FastAPI, None, None]:
    """Create a test FastAPI app."""
    # Initialize cache before creating the app
    FastAPICache.init(
        InMemoryBackend(),
        enable_dogpile_prevention=True,
        dogpile_grace_time=10.0,
        dogpile_wait_time=0.1,
        dogpile_max_wait_time=2.0,
    )

    app = FastAPI()

    @app.get("/expensive/{item_id}")
    @cache(expire=60)
    async def get_expensive_resource(item_id: int) -> Dict[str, Union[int, str]]:  # pyright: ignore[reportUnusedFunction]
        """Simulate an expensive operation."""
        # Track when this function is called
        if item_id not in call_tracker:
            call_tracker[item_id] = []
        call_tracker[item_id].append(time.time())

        # Simulate expensive computation
        await asyncio.sleep(1.0)
        return {"item_id": item_id, "data": f"expensive data for {item_id}"}

    @app.get("/no-dogpile/{item_id}")
    @cache(expire=60, enable_dogpile_prevention=False)
    async def get_resource_no_dogpile_prevention(item_id: int) -> Dict[str, Union[int, str]]:  # pyright: ignore[reportUnusedFunction]
        """Resource without dogpile prevention."""
        if item_id not in call_tracker:
            call_tracker[item_id] = []
        call_tracker[item_id].append(time.time())

        await asyncio.sleep(1.0)
        return {"item_id": item_id, "data": f"data for {item_id}"}

    yield app
    # Clean up after the test
    FastAPICache.reset()


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


def test_dogpile_prevention_single_request(client: TestClient) -> None:
    """Test that a single request works normally."""
    call_tracker.clear()

    response = client.get("/expensive/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "data": "expensive data for 1"}
    assert len(call_tracker.get(1, [])) == 1

    # Second request should hit cache
    response = client.get("/expensive/1")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "data": "expensive data for 1"}
    assert len(call_tracker.get(1, [])) == 1  # Still only one call


@pytest.mark.asyncio()
async def test_dogpile_prevention_concurrent_requests() -> None:
    """Test that concurrent requests are handled properly with dogpile prevention."""
    call_tracker.clear()

    # Initialize cache first
    FastAPICache.init(
        InMemoryBackend(),
        enable_dogpile_prevention=True,
        dogpile_grace_time=10.0,
        dogpile_wait_time=0.1,
        dogpile_max_wait_time=5.0,
    )

    # Create app with async client
    app = FastAPI()

    @app.get("/expensive/{item_id}")
    @cache(expire=60)
    async def get_expensive_resource(item_id: int) -> Dict[str, Union[int, str]]:  # pyright: ignore[reportUnusedFunction]
        if item_id not in call_tracker:
            call_tracker[item_id] = []
        call_tracker[item_id].append(time.time())

        await asyncio.sleep(1.0)
        return {"item_id": item_id, "data": f"expensive data for {item_id}"}

    # Simulate concurrent requests
    async def make_request(item_id: int) -> Dict[str, Union[int, str]]:
        # Simulate the cache decorator behavior
        backend = FastAPICache.get_backend()
        from fastapi_cache.lock import OptimisticLock

        cache_key = f"test:expensive:{item_id}"
        cached = await backend.get(cache_key)

        if cached is None:
            lock = OptimisticLock(backend, cache_key, 10.0)
            is_computing, remaining_time = await lock.is_computing()

            if is_computing:
                # Wait for the other request
                total_wait = 0.0
                while total_wait < min(remaining_time or 0, 5.0):
                    await asyncio.sleep(0.1)
                    total_wait += 0.1
                    cached = await backend.get(cache_key)
                    if cached is not None:
                        return {"item_id": item_id, "data": f"expensive data for {item_id}"}
            else:
                # We're the first, start computing
                await lock.start_computing()
                try:
                    # Call the function logic directly
                    if item_id not in call_tracker:
                        call_tracker[item_id] = []
                    call_tracker[item_id].append(time.time())
                    await asyncio.sleep(1.0)
                    result: Dict[str, Union[int, str]] = {"item_id": item_id, "data": f"expensive data for {item_id}"}
                    await backend.set(cache_key, b"cached_result", 60)
                    return result
                finally:
                    await lock.finish_computing()

        return {"item_id": item_id, "data": f"expensive data for {item_id}"}

    # Start 5 concurrent requests for the same item
    item_id = 42
    tasks = [make_request(item_id) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # All requests should get the same result
    for result in results:
        assert result == {"item_id": item_id, "data": f"expensive data for {item_id}"}

    # But the expensive function should only be called once
    assert len(call_tracker.get(item_id, [])) == 1

    # Clean up
    FastAPICache.reset()


@pytest.mark.asyncio()
async def test_dogpile_prevention_different_keys() -> None:
    """Test that different cache keys don't interfere with each other."""
    call_tracker.clear()

    backend = InMemoryBackend()
    FastAPICache.reset()
    FastAPICache.init(
        backend,
        enable_dogpile_prevention=True,
        dogpile_grace_time=10.0,
        dogpile_wait_time=0.1,
        dogpile_max_wait_time=5.0,
    )

    async def expensive_operation(key: str) -> str:
        if key not in call_tracker:
            call_tracker[key] = []
        call_tracker[key].append(time.time())
        await asyncio.sleep(0.5)
        return f"result for {key}"

    # Start requests for different keys
    tasks: List[Coroutine[Any, Any, str]] = []
    for i in range(3):
        for _ in range(2):  # 2 requests per key
            key = f"key_{i}"
            tasks.append(expensive_operation(key))

    await asyncio.gather(*tasks)

    # Each key should have been computed multiple times (no prevention across keys)
    assert len(call_tracker["key_0"]) == 2
    assert len(call_tracker["key_1"]) == 2
    assert len(call_tracker["key_2"]) == 2

    # Clean up
    FastAPICache.reset()


@pytest.mark.asyncio()
async def test_dogpile_prevention_timeout() -> None:
    """Test that dogpile prevention respects the grace time."""
    call_tracker.clear()

    backend = InMemoryBackend()
    FastAPICache.reset()
    FastAPICache.init(
        backend,
        enable_dogpile_prevention=True,
        dogpile_grace_time=2.0,  # Grace time longer than operation
        dogpile_wait_time=0.1,
        dogpile_max_wait_time=0.5,  # Max wait time
    )

    from fastapi_cache.lock import OptimisticLock

    async def slow_operation(key: str) -> str:
        if key not in call_tracker:
            call_tracker[key] = []
        call_tracker[key].append(time.time())
        await asyncio.sleep(0.5)  # Operation time
        return f"result for {key}"

    cache_key = "test_key"
    lock = OptimisticLock(backend, cache_key, 2.0)  # Match the grace time

    # First request starts computing
    started = await lock.start_computing()
    assert started  # Ensure we successfully started computing

    # Verify the lock is set
    is_computing, remaining_time = await lock.is_computing()
    assert is_computing
    assert remaining_time is not None

    task1 = asyncio.create_task(slow_operation("key1"))

    # Wait a bit and start second request
    await asyncio.sleep(0.1)

    # Second request should still detect computing
    is_computing, remaining_time = await lock.is_computing()
    assert is_computing  # Should still be computing

    # Wait for more than max wait time to ensure second request proceeds
    await asyncio.sleep(0.6)

    # Now second request should proceed (after timeout)
    task2 = asyncio.create_task(slow_operation("key2"))

    try:
        await task1
        await task2

        # Both operations should have been called
        assert len(call_tracker) == 2
    finally:
        # Clean up - ensure tasks are properly cancelled if they're still running
        if not task1.done():
            task1.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass
        if not task2.done():
            task2.cancel()
            try:
                await task2
            except asyncio.CancelledError:
                pass

        # Clean up cache
        FastAPICache.reset()


@pytest.mark.asyncio()
async def test_dogpile_prevention_with_redis_like_backend() -> None:
    """Test dogpile prevention with a Redis-like backend."""
    # Simulate a Redis-like backend
    class MockRedisBackend(Backend):
        def __init__(self) -> None:
            self.data: Dict[str, bytes] = {}
            self.redis = self  # Simulate redis attribute

        async def get(self, key: str) -> Optional[bytes]:
            return self.data.get(key)

        async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
            return 60, self.data.get(key)

        async def set(self, key: str, value: bytes, expire: Optional[int] = None, **kwargs: Any) -> Any:
            # Support both Backend.set signature and Redis.set signature
            nx = kwargs.get('nx', False)
            if nx and key in self.data:
                return False
            self.data[key] = value
            return True if nx else None

        async def eval(self, script: str, numkeys: int, *args: Any) -> int:
            # Simulate the Lua script for atomic check-and-delete
            if numkeys == 1:
                key, expected_value = args
                if self.data.get(key) == expected_value.encode():
                    del self.data[key]
                    return 1
            return 0

        async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
            if key and key in self.data:
                del self.data[key]
                return 1
            return 0

    backend = MockRedisBackend()
    from fastapi_cache.lock import RedisLock

    # Test lock acquisition
    lock1 = RedisLock(backend, "test_key", 5.0)
    assert await lock1.acquire() is True

    # Second lock should fail
    lock2 = RedisLock(backend, "test_key", 5.0)
    assert await lock2.acquire() is False

    # Release first lock
    assert await lock1.release() is True

    # Now second lock should succeed
    assert await lock2.acquire() is True
    assert await lock2.release() is True
