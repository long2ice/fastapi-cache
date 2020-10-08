import time
from dataclasses import dataclass
from threading import Lock
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

    def _get(self, key: str):
        v = self._store.get(key)
        if v:
            if v.ttl_ts < self._now:
                del self._store[key]
            else:
                return v

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[str]]:
        with self._lock:
            v = self._get(key)
            if v:
                return v.ttl_ts - self._now, v.data
            return 0, None

    async def get(self, key: str) -> str:
        with self._lock:
            v = self._get(key)
            if v:
                return v.data

    async def set(self, key: str, value: str, expire: int = None):
        with self._lock:
            self._store[key] = Value(value, self._now + expire)
