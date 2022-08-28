from itertools import groupby
from operator import itemgetter
from time import time
from typing import Tuple, Union

from fastapi_cache.backends import Backend

from diskcache import Cache, FanoutCache


class DiskCacheBackend(Backend):
    def __init__(self, diskcache: Union[Cache, FanoutCache]):
        self.cache = diskcache

    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        with self.cache.transact(retry=True):
            value, ttl = self.cache.get(key, expire_time=True, retry=True)  # type: ignore
            return ttl, value

    async def get(self, key) -> str:
        return self.cache.get(key, retry=True)  # type: ignore

    async def set(self, key: str, value: str, expire: Union[int, None] = None):
        return self.cache.set(key, value, expire=expire, retry=True)

    async def clear(self, namespace: Union[str, None] = None, key: Union[str, None] = None) -> int:
        if namespace:
            if isinstance(self.cache, FanoutCache):
                caches = self.cache._shards
                result = [self._clear(cache, namespace) for cache in caches]
                return sum(result)
            return self._clear(self.cache, namespace)

        elif key:
            if self.cache.delete(key, retry=True):
                return 1
            else:
                return 0
        return 0

    def _clear(self, cache: Cache, namespace: str) -> int:
        keys = {
            key: cache.disk.put(key)
            for key in cache.iterkeys()
            if isinstance(key, str) and key.startswith(namespace)
        }

        with cache._transact(retry=True) as (sql, cleanup):
            now = time()
            rows = sql(
                "select rowid, filename, key, raw from Cache"
                " where key in ?"
                " and (expire_time is null or expire_time > ?",
                (f"({','.join(keys.keys())})", now),
            ).fetchall()

            selected_rows = [
                (rowid, filename) for rowid, filename, key, raw in rows if keys[key] == raw
            ]

            if not selected_rows:
                return 0

            sorted_rows = sorted(selected_rows, key=itemgetter(1))
            for filename, group in groupby(sorted_rows, key=itemgetter(1)):
                sql(
                    "delete from Cache where rowid in ?",
                    (f"({','.join(str(rowid) for rowid, _ in group)})",),
                )
                cleanup(filename)

            return len(sorted_rows)
