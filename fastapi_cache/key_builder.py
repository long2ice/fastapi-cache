import hashlib
from collections.abc import Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import Response


def default_key_builder(
    func: Callable[..., Any],
    namespace: str = "",
    *,
    request: Request | None = None,
    response: Response | None = None,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    cache_key = hashlib.md5(  # noqa: S324
        f"{func.__module__}:{func.__name__}:{args}:{kwargs}".encode()
    ).hexdigest()
    return f"{namespace}:{cache_key}"
