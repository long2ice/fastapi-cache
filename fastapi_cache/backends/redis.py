from typing import Tuple

from aioredis import Redis

from fastapi_cache.backends import Backend


class RedisBackend(Backend):
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_with_ttl(self, name: str) -> Tuple[int, str]:
        p = self.redis.pipeline()
        p.ttl(name)
        p.get(name)
        return await p.execute()

    async def get(self, name) -> str:
        return await self.redis.get(name)

    async def set(self, name: str, value: str, ex: int = None):
        return await self.redis.set(name, value, ex=ex)

    async def clear(self, namespace: str = None, name: str = None) -> int:
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.redis.eval(lua)
        elif name:
            return await self.redis.delete(name)
