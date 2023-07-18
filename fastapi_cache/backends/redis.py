from typing import Optional, Tuple, Union

from redis.asyncio.client import Redis
from redis.asyncio.cluster import RedisCluster

from fastapi_cache.types import Backend


class RedisBackend(Backend):
    def __init__(self, redis: Union["Redis[bytes]", "RedisCluster[bytes]"]):
        self.redis = redis
        self.is_cluster: bool = isinstance(redis, RedisCluster)

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        async with self.redis.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()  # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> Optional[bytes]:
        return await self.redis.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        await self.redis.set(key, value, ex=expire)  # type: ignore[union-attr]

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if namespace:
            cursor = 0
            removed = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, f'{namespace}:*', 500)  # type: ignore[union-attr]
                removed += await self.redis.delete(*keys)  # type: ignore[union-attr]
                if cursor == 0:
                    return removed
        elif key:
            return await self.redis.delete(key)  # type: ignore[union-attr]
        return 0
