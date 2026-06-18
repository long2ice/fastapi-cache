import abc
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response
from typing_extensions import Protocol

_Func = Callable[..., Any]


class KeyBuilder(Protocol):
    def __call__(
        self,
        __function: _Func,
        __namespace: str = ...,
        *,
        request: Request | None = ...,
        response: Response | None = ...,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Awaitable[str] | str:
        ...


class Backend(abc.ABC):
    @abc.abstractmethod
    async def get_with_ttl(self, key: str) -> tuple[int, bytes | None]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, key: str, value: bytes, expire: int | None = None) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def clear(self, namespace: str | None = None, key: str | None = None) -> int:
        raise NotImplementedError
