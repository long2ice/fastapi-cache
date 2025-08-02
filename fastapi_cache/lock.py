"""Lock implementations for dogpile prevention in fastapi-cache."""
import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type, cast

from fastapi_cache.types import Backend

if TYPE_CHECKING:
    from fastapi_cache.backends.redis import RedisBackend

logger = logging.getLogger(__name__)


class LockError(Exception):
    """Base exception for lock-related errors."""
    pass


class DogpileLock(ABC):
    """Abstract base class for dogpile prevention locks."""

    def __init__(self, backend: Backend, key: str, lease: float):
        self.backend = backend
        self.key = key
        self.lease = lease
        self._lock_key = f"__lock:{key}"
        self._identifier = str(uuid.uuid4())

    @abstractmethod
    async def acquire(self) -> bool:
        """Try to acquire the lock."""
        raise NotImplementedError

    @abstractmethod
    async def release(self) -> bool:
        """Release the lock."""
        raise NotImplementedError

    async def __aenter__(self) -> "DogpileLock":
        """Async context manager entry."""
        if not await self.acquire():
            raise LockError(f"Failed to acquire lock for key: {self.key}")
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        """Async context manager exit."""
        await self.release()


class RedisLock(DogpileLock):
    """Redis-based implementation of dogpile lock using SET NX with expiration."""

    async def acquire(self) -> bool:
        """Try to acquire the lock using Redis SET NX."""
        try:
            # Try to set the lock key with NX (only if not exists) and EX (expiration)
            # We need to use the raw Redis client for this
            if hasattr(self.backend, 'redis'):
                # For RedisBackend
                redis_backend = cast("RedisBackend", self.backend)
                result = await redis_backend.redis.set(  # type: ignore[union-attr]
                    self._lock_key,
                    self._identifier.encode(),
                    nx=True,
                    ex=int(self.lease)
                )
                return bool(result)  # pyright: ignore[reportUnknownArgumentType]
            else:
                # Fallback for other backends - use basic set if get is None
                existing = await self.backend.get(self._lock_key)
                if existing is None:
                    await self.backend.set(self._lock_key, self._identifier.encode(), int(self.lease))
                    return True
                return False
        except Exception:
            return False

    async def release(self) -> bool:
        """Release the lock only if we own it."""
        try:
            if hasattr(self.backend, 'redis'):
                # Use Lua script to ensure atomic check-and-delete
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                redis_backend = cast("RedisBackend", self.backend)
                result = await redis_backend.redis.eval(  # type: ignore[union-attr]
                    lua_script,
                    1,
                    self._lock_key,
                    self._identifier
                )
                return bool(result)  # pyright: ignore[reportUnknownArgumentType]
            else:
                # Fallback - just delete (not atomic but better than nothing)
                value = await self.backend.get(self._lock_key)
                if value and value.decode() == self._identifier:
                    await self.backend.clear(key=self._lock_key)
                    return True
                return False
        except Exception:
            return False


class InMemoryLock(DogpileLock):
    """In-memory implementation of dogpile lock for single-process scenarios."""

    # Class-level lock storage
    _locks: Dict[str, Tuple[float, str]] = {}
    _lock: asyncio.Lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire the lock in memory."""
        async with self._lock:
            now = time.time()

            # Check if lock exists and is still valid
            if self._lock_key in self._locks:
                lock_time, _ = self._locks[self._lock_key]
                if now < lock_time + self.lease:
                    # Lock is still valid
                    return False

            # Acquire the lock
            self._locks[self._lock_key] = (now, self._identifier)
            return True

    async def release(self) -> bool:
        """Release the lock if we own it."""
        async with self._lock:
            if self._lock_key in self._locks:
                _, lock_id = self._locks[self._lock_key]
                if lock_id == self._identifier:
                    del self._locks[self._lock_key]
                    return True
            return False


class OptimisticLock:
    """
    Optimistic lock implementation for dogpile prevention.

    This lock allows the first request to proceed with computation while
    subsequent requests wait and then use the computed value.
    """

    def __init__(self, backend: Backend, key: str, grace_time: float = 60.0):
        self.backend = backend
        self.key = key
        self.grace_time = grace_time
        self._computing_key = f"__computing:{key}"
        self._identifier = str(uuid.uuid4())
        self._start_time: Optional[float] = None

    async def is_computing(self) -> Tuple[bool, Optional[float]]:
        """Check if another process is computing the value."""
        computing_data = await self.backend.get(self._computing_key)
        if computing_data:
            try:
                # Store timestamp when computation started
                start_time = float(computing_data.decode())
                elapsed = time.time() - start_time
                if elapsed < self.grace_time:
                    return True, self.grace_time - elapsed
            except (ValueError, AttributeError):
                pass
        return False, None

    async def start_computing(self) -> bool:
        """Mark that we're starting to compute the value."""
        # Try to set the computing flag with current timestamp
        try:
            # Check if someone else is already computing
            is_computing, _ = await self.is_computing()
            if is_computing:
                return False

            # Set the computing flag with current timestamp
            self._start_time = time.time()
            await self.backend.set(
                self._computing_key,
                str(self._start_time).encode(),
                int(self.grace_time)
            )
            return True
        except Exception:
            return False

    async def finish_computing(self) -> None:
        """Mark that we've finished computing the value."""
        try:
            # Only clear if we were the ones computing
            if self._start_time:
                computing_data = await self.backend.get(self._computing_key)
                if computing_data:
                    stored_time = float(computing_data.decode())
                    if abs(stored_time - self._start_time) < 0.001:  # Allow small float precision errors
                        await self.backend.clear(key=self._computing_key)
        except Exception as e:
            logger.debug(f"Error while finishing computing for key {self._computing_key}: {e}")


def create_lock(backend: Backend, key: str, lease: float) -> DogpileLock:
    """Factory function to create appropriate lock based on backend type."""
    backend_class = backend.__class__.__name__

    if backend_class == "RedisBackend":
        return RedisLock(backend, key, lease)
    elif backend_class == "InMemoryBackend":
        return InMemoryLock(backend, key, lease)
    else:
        # For other backends, try Redis-style lock first
        return RedisLock(backend, key, lease)
