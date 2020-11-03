import abc
from typing import Tuple


class Backend:
    @abc.abstractmethod
    async def get_with_ttl(self, key: str) -> Tuple[int, str]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: str) -> str:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: str, expire: int = None):
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, namespace: str = None, key: str = None) -> int:
        raise NotImplementedError
