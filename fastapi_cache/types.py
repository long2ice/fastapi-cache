from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Union

from starlette.requests import Request
from starlette.responses import Response
from typing_extensions import Protocol


_Func = Callable[..., Any]


class KeyBuilder(Protocol):
    def __call__(
        self,
        _function: _Func,
        _namespace: str = ...,
        *,
        request: Optional[Request] = ...,
        response: Optional[Response] = ...,
        args: Tuple[Any, ...] = ...,
        kwargs: Dict[str, Any] = ...,
    ) -> Union[Awaitable[str], str]:
        ...
