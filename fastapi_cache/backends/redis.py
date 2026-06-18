from typing import Union

from redis.asyncio.client import Redis
from redis.asyncio.cluster import RedisCluster

from fastapi_cache.types import Backend


class RedisBackend(Backend):
    def __init__(self, redis: Union["Redis[bytes]", "RedisCluster[bytes]"]):
        self.redis = redis
        self.is_cluster: bool = isinstance(redis, RedisCluster)

    async def get_with_ttl(self, key: str) -> tuple[int, bytes | None]:
        async with self.redis.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()  # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> bytes | None:
        return await self.redis.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: bytes, expire: int | None = None) -> None:
        await self.redis.set(key, value, ex=expire)  # type: ignore[union-attr]

    async def clear(self, namespace: str | None = None, key: str | None = None) -> int:
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.redis.eval(lua, numkeys=0)  # type: ignore[union-attr,no-any-return]
        elif key:
            return await self.redis.delete(key)  # type: ignore[union-attr]
        return 0
