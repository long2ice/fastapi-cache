from typing import Optional, Tuple

from redis.asyncio.client import AbstractRedis
from redis.asyncio.cluster import AbstractRedisCluster

from fastapi_cache.backends import Backend


class RedisBackend(Backend):
    def __init__(self, redis: AbstractRedis):
        self.redis = redis
        self.is_cluster = isinstance(redis, AbstractRedisCluster)

    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        async with self.redis.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        return await self.redis.set(key, value, ex=expire)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.redis.eval(lua, numkeys=0)
        elif key:
            return await self.redis.delete(key)
        return 0
