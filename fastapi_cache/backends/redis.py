from typing import Optional, Tuple, Union

from redis.asyncio.client import Redis
from redis.asyncio.cluster import RedisCluster

from fastapi_cache.types import Backend


class RedisBackend(Backend):
    def __init__(self, redis: Union["Redis[bytes]", "RedisCluster[bytes]"]):
        self.redis = redis
        self.is_cluster: bool = isinstance(redis, RedisCluster)
        # Add driver identification for redis-py
        self._add_driver_info()

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        async with self.redis.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()  # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> Optional[bytes]:
        return await self.redis.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        await self.redis.set(key, value, ex=expire)  # type: ignore[union-attr]

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.redis.eval(lua, numkeys=0)  # type: ignore[union-attr,no-any-return]
        elif key:
            return await self.redis.delete(key)  # type: ignore[union-attr]
        return 0

    def _add_driver_info(self) -> None:
        """Add driver identification to Redis connection.

        Uses DriverInfo class if available, or falls back to
        lib_name/lib_version for older versions.
        """
        from typing import Any

        from fastapi_cache import __version__

        # Get connection pool from the redis client
        connection_pool: Any = getattr(self.redis, "connection_pool", None)
        if connection_pool is None:
            return

        # Try to use DriverInfo class
        try:
            from redis import DriverInfo

            driver_info = DriverInfo().add_upstream_driver("fastapi-cache", __version__)
            connection_pool.connection_kwargs["driver_info"] = driver_info
        except (ImportError, AttributeError):
            # Fallback: use lib_name/lib_version
            # Format: lib_name='redis-py(fastapi-cache_v{version})'
            connection_pool.connection_kwargs["lib_name"] = f"redis-py(fastapi-cache_v{__version__})"
            # lib_version should be the redis client version
            try:
                import redis

                redis_version = redis.__version__
            except (ImportError, AttributeError):
                redis_version = "unknown"
            connection_pool.connection_kwargs["lib_version"] = redis_version
