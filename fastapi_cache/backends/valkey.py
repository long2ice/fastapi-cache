"""
fastapi-cache - Valkey cache backend support
"""
from typing import Optional, Tuple, Union

from valkey.asyncio.client import Valkey
from valkey.asyncio.cluster import ValkeyCluster

from fastapi_cache.types import Backend


class ValkeyBackend(Backend):
    """
    Valkey cache backend
    """

    def __init__(self, valkey: Union[Valkey, ValkeyCluster]):
        self.valkey = valkey
        self.is_cluster: bool = isinstance(valkey, ValkeyCluster)

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        async with self.valkey.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()   # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> Optional[bytes]:
        return await self.valkey.get(key)   # type: ignore[no-any-return]

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        await self.valkey.set(key, value, ex=expire)

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if namespace:
            lua = f"for i, name in ipairs(redis.call('KEYS', '{namespace}:*')) do redis.call('DEL', name); end"
            return await self.valkey.eval(lua, numkeys=0)   # type: ignore[misc,no-any-return]
        if key:
            return await self.valkey.delete(key)    # type: ignore[no-any-return]
        return 0
