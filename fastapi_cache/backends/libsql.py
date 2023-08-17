import codecs
import time
from typing import Any, Optional, Tuple

import libsql_client
from libsql_client import ResultSet

from fastapi_cache.types import Backend

EmptyResultSet = ResultSet(
    columns=(),
    rows=[],
    rows_affected=0,
    last_insert_rowid=0)

# see https://gist.github.com/jeremyBanks/1083518
def quote_identifier(s:str, errors:str ="strict") -> str:
    encodable = s.encode("utf-8", errors).decode("utf-8")

    nul_index = encodable.find("\x00")

    if nul_index >= 0:
        error = UnicodeEncodeError("utf-8", encodable, nul_index, nul_index + 1, "NUL not allowed")
        error_handler = codecs.lookup_error(errors)
        replacement, _ = error_handler(error)
        encodable = encodable.replace("\x00", replacement) # type: ignore

    return "\"" + encodable.replace("\"", "\"\"") + "\""


class LibsqlBackend(Backend):
    """
    libsql backend provider

    This backend requires a table name to be passed during initialization. The table
    will be created if it does not exist. If the table does exists, it will be emptied during init

    Note that this backend does not fully support TTL. It will only delete outdated objects on get.

    Usage:
        >> libsql_url = "file:local.db"
        >> cache = LibsqlBackend(libsql_url=libsql_url, table_name="your-cache")
        >> cache.create_and_flush()
        >> FastAPICache.init(cache)
    """

    # client: libsql_client.Client
    table_name: str
    libsql_url: str

    def __init__(self, libsql_url: str, table_name: str):
        self.libsql_url = libsql_url
        self.table_name = quote_identifier(table_name)

    @property
    def now(self) -> int:
        return int(time.time())

    async def _make_request(self, request: str, params: Any = None) -> ResultSet:
        # TODO: Exception handling. Return EmptyResultSet on error?
        async with libsql_client.create_client(self.libsql_url) as client:
            return await client.execute(request, params)


    async def create_and_flush(self) -> None:
        await self._make_request(f"CREATE TABLE IF NOT EXISTS {self.table_name} "
                                "(key STRING PRIMARY KEY, value BLOB , expire INTEGER)") # noqa: S608
        await self._make_request(f"DELETE FROM {self.table_name}") # noqa: S608

        return None

    async def _get(self, key: str) -> Tuple[int, Optional[bytes]]:
        result_set = await self._make_request(f"SELECT * from {self.table_name} WHERE key = ?", # noqa: S608
                                              [key])
        if len(result_set.rows) == 0:
            return (0,None)

        value = result_set.rows[0]["value"]
        ttl_ts = result_set.rows[0]["expire"]

        if not value:
            return (0,None)
        if ttl_ts < self.now:
            await self._make_request(f"DELETE FROM {self.table_name} WHERE key = ?", # noqa: S608
                                     [key])
            return (0, None)

        return(ttl_ts, value)  # type: ignore[union-attr,no-any-return]

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        return await self._get(key)

    async def get(self, key: str) -> Optional[bytes]:
        _, value = await self._get(key)
        return value

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        ttl = self.now + expire if expire else 0
        await self._make_request(f"INSERT OR REPLACE INTO {self.table_name}(\"key\", \"value\", \"expire\") "
                                 "VALUES(?,?,?)", # noqa: S608
                                 [key, value, ttl])
        return None

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:

        if namespace:
            result_set = await self._make_request(f"DELETE FROM {self.table_name} WHERE key = ?", # noqa: S608
                                                  [namespace + '%'])
            return result_set.rowcount # type: ignore
        elif key:
            result_set = await self._make_request(f"DELETE FROM {self.table_name} WHERE key = ?", # noqa: S608
                                                  [key])
            return result_set.rowcount # type: ignore
        return 0
