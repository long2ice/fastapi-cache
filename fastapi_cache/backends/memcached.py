from typing import Tuple

from aiomcache import Client

from fastapi_cache.backends import Backend


class MemcachedBackend(Backend):
    def __init__(self, mcache: Client):
        self.mcache = mcache

    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        return 3600, await self.mcache.get(key.encode())

    async def get(self, key: str):
        return await self.mcache.get(key, key.encode())

    async def set(self, key: str, value: str, expire: int = None):
        return await self.mcache.set(key.encode(), value.encode(), exptime=expire or 0)

    async def clear(self, namespace: str = None, key: str = None):
        raise NotImplementedError
