import time
from typing import Optional, Tuple

import libsql_client
from libsql_client import ResultSet

from fastapi_cache.types import Backend

EmptyResultSet = ResultSet(
    columns=(),
    rows=[], 
    rows_affected=0, 
    last_insert_rowid=0)

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
        self.table_name = table_name 

    @property
    def now(self) -> int:
        return int(time.time())
    
    async def _make_request(self, request: str) -> ResultSet:
        # TODO: Exception handling. Return EmptyResultSet on error?
        async with libsql_client.create_client(self.libsql_url) as client:
            return await client.execute(request)


    async def create_and_flush(self) -> None:
        await self._make_request("CREATE TABLE IF NOT EXISTS `{}` "
                                "(key STRING PRIMARY KEY, value BLOB, expire INTEGER);"
                                .format(self.table_name))
        await self._make_request("DELETE FROM `{}`;".format(self.table_name))

        return None

    async def _get(self, key: str) -> Tuple[int, Optional[bytes]]:
        result_set = await self._make_request("SELECT * from `{}` WHERE key = \"{}\""
                                              .format(self.table_name,key))
        if len(result_set.rows) == 0:
            return (0,None)
        
        value = result_set.rows[0]["value"]
        ttl_ts = result_set.rows[0]["expire"]
        
        if not value:
            return (0,None)
        if ttl_ts < self.now:
            await self._make_request("DELETE FROM `{}` WHERE key = \"{}\""
                                     .format(self.table_name, key))
            return (0, None)
        
        return(ttl_ts, value)  # type: ignore[union-attr,no-any-return]

    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[bytes]]:
        return await self._get(key)

    async def get(self, key: str) -> Optional[bytes]:
        _, value = await self._get(key)
        return value

    async def set(self, key: str, value: bytes, expire: Optional[int] = None) -> None:
        ttl = self.now + expire if expire else 0
        await self._make_request("INSERT OR REPLACE INTO `{}`(\"key\", \"value\", \"expire\") " 
                                 "VALUES('{}','{}',{});"
                                 .format(self.table_name, key, value.decode("utf-8"), ttl))
        return None

    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:

        if namespace:
            result_set = await self._make_request("DELETE FROM `{}` WHERE key = \"{}%\""
                                                  .format(self.table_name, namespace))
            return result_set.rowcount # type: ignore
        elif key:
            result_set = await self._make_request("DELETE FROM `{}` WHERE key = \"{}\""
                                                  .format(self.table_name, key))
            return result_set.rowcount # type: ignore
        return 0
