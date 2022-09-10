from contextvars import ContextVar
from typing import Tuple, Optional

from fastapi import Request, Response

_request_response_val = ContextVar("_request_response_val")


def get_cache_ctx() -> Tuple[Optional[Request], Optional[Response]]:
    return _request_response_val.get(default=(None, None))


async def cache_ctx(
    request: Request,
    response: Response,
) -> None:
    _request_response_val.set((request, response))
