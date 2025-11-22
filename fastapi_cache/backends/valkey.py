from typing import Optional, Tuple, Union

from valkey.asyncio import Valkey
from valkey.asyncio.cluster import ValkeyCluster

from fastapi_cache.types import Backend


class ValkeyBackend(Backend):
    def __init__(self, valkey: Union["Valkey[bytes]", "ValkeyCluster[bytes]"]):
        self.valkey = valkey
        self.is_cluster: bool = isinstance(valkey, ValkeyCluster)

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        async with self.valkey.pipeline(transaction=not self.is_cluster) as pipe:
            return await pipe.ttl(key).get(key).execute()  # type: ignore[union-attr,no-any-return]

    async def get(self, key: str) -> Optional[bytes]:
        return await self.valkey.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        await self.valkey.set(key, value, ex=expire)  # type: ignore[union-attr]

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        if namespace:
            cursor = 0
            deleted = 0
            pattern = f"{namespace}:*"
            
            while True:
                cursor, keys = await self.valkey.scan(cursor, match=pattern, count=100)  # type: ignore[union-attr]
                if keys:
                    deleted += await self.valkey.delete(*keys)  # type: ignore[union-attr]
                if cursor == 0:
                    break
            
            return deleted
        elif key:
            return await self.valkey.delete(key)  # type: ignore[union-attr]
        return 0