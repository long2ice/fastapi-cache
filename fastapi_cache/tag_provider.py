import asyncio
from typing import Callable, List, Optional, Union

from fastapi_cache import FastAPICache
from fastapi_cache.types import ItemsProviderProtocol


class TagProvider:
    def __init__(
        self,
        object_type: str,
        object_id_provider: Optional[Callable[[dict], str]] = None,
    ) -> None:
        self.object_type = object_type
        self.object_id_provider = object_id_provider or self.default_object_id_provider

    @staticmethod
    def default_object_id_provider(item: dict) -> str:
        return f"{item['id']}"

    @staticmethod
    def default_items_provider(
        data: Union[dict, list],
        method_args: Optional[tuple] = None,
        method_kwargs: Optional[dict] = None,
    ) -> list[dict]:
        return data

    def get_tag(self, item: Optional[dict] = None, object_id: Optional[str] = None) -> str:
        prefix = FastAPICache.get_prefix()
        object_id = object_id or self.object_id_provider(item)
        return f"{prefix}:invalidation:{self.object_type}:{object_id}"

    @staticmethod
    async def _append_value(key: str, parent_key: str, expire: int):
        backend = FastAPICache.get_backend()
        coder = FastAPICache.get_coder()
        value = await backend.get(key)
        if value:
            value = coder.decode(value)
            value.append(parent_key)
        else:
            value = [parent_key]
        await backend.set(key=key, value=coder.encode(value), expire=expire)

    async def provide(
        self,
        data: Union[dict, list],
        parent_key: str,
        expire: Optional[int] = None,
        items_provider: Optional[ItemsProviderProtocol] = None,
        method_args: Optional[tuple] = None,
        method_kwargs: Optional[dict] = None,
    ) -> None:
        """
        Provides tags for endpoint.

        :param data:
        :param parent_key:
        :param expire:
        :param items_provider:
        :param method_args:
        :param method_kwargs:
        """
        provider = items_provider or self.default_items_provider
        tasks = [
            self._append_value(
                key=self.get_tag(item),
                parent_key=parent_key,
                expire=expire or FastAPICache.get_expire(),
            )
            for item in provider(data, method_args, method_kwargs)
        ]
        await asyncio.gather(*tasks)

    async def invalidate(self, object_id: str) -> None:
        """
        Invalidate tags with given object_id

        :param object_id: object_id to invalidate
        """
        backend = FastAPICache.get_backend()
        coder = FastAPICache.get_coder()
        tag = self.get_tag(object_id=object_id)

        value = await backend.get(tag)
        if not value:
            return

        keys: List[str] = coder.decode(value)
        tasks = [backend.clear(key=key) for key in keys]
        tasks.append(backend.clear(key=tag))
        await asyncio.gather(*tasks)
