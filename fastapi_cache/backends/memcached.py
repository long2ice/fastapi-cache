from typing import Optional, Tuple

from aiomcache import Client

from fastapi_cache.backends import Backend


class MemcachedBackend(Backend):
    def __init__(self, mcache: Client):
        self.mcache = mcache

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[str]]:
        return 3600, await self.mcache.get(key.encode())

    async def get(self, key: str) -> Optional[str]:
        return await self.mcache.get(key, key.encode())

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        await self.mcache.set(key.encode(), value.encode(), exptime=expire or 0)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        raise NotImplementedError
