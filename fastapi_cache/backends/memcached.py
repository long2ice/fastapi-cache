
from aiomcache import Client

from fastapi_cache.types import Backend


class MemcachedBackend(Backend):
    def __init__(self, mcache: Client):
        self.mcache = mcache

    async def get_with_ttl(self, key: str) -> tuple[int, bytes | None]:
        return 3600, await self.get(key)

    async def get(self, key: str) -> bytes | None:
        return await self.mcache.get(key.encode())

    async def set(self, key: str, value: bytes, expire: int | None = None) -> None:
        await self.mcache.set(key.encode(), value, exptime=expire or 0)

    async def clear(self, namespace: str | None = None, key: str | None = None) -> int:
        raise NotImplementedError
