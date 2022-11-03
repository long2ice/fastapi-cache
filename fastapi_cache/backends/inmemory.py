import time
from asyncio import Lock
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from fastapi_cache.backends import Backend


@dataclass
class Value:
    data: str
    ttl_ts: int


class InMemoryBackend(Backend):
    _store: Dict[str, Value] = {}
    _lock = Lock()

    @property
    def _now(self) -> int:
        return int(time.time())

    def _get(self, key: str) -> Optional[Value]:
        v = self._store.get(key)
        if v:
            if v.ttl_ts < self._now:
                del self._store[key]
            else:
                return v
        return None

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[str]]:
        async with self._lock:
            v = self._get(key)
            if v:
                return v.ttl_ts - self._now, v.data
            return 0, None

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            v = self._get(key)
            if v:
                return v.data
            return None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        async with self._lock:
            self._store[key] = Value(value, self._now + (expire or 0))

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        count = 0
        if namespace:
            keys = list(self._store.keys())
            for key in keys:
                if key.startswith(namespace):
                    del self._store[key]
                    count += 1
        elif key:
            del self._store[key]
            count += 1
        return count
