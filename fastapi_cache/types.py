from typing import Any, Awaitable, Callable, Optional, Protocol, Union

from starlette.requests import Request
from starlette.responses import Response


_Func = Callable[..., Any]


class KeyBuilder(Protocol):
    def __call__(
        self,
        _function: _Func,
        _namespace: str = ...,
        *,
        request: Optional[Request] = ...,
        response: Optional[Response] = ...,
        args: tuple[Any, ...] = ...,
        kwargs: dict[str, Any] = ...,
    ) -> Union[Awaitable[str], str]:
        ...
