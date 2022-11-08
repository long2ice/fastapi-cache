import abc
from typing import Optional, Tuple


class Backend:
    @abc.abstractmethod
    async def get_with_ttl(self, key: str) -> Tuple[int, Optional[str]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, namespace: Optional[str] = None, key: Optional[str] = None) -> int:
        raise NotImplementedError
