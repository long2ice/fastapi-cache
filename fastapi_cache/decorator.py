import inspect
import logging
import sys
from functools import wraps
from typing import Awaitable, Callable, Optional, Type, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi.concurrency import run_in_threadpool
from fastapi.dependencies.utils import get_typed_return_annotation
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder
from fastapi_cache.types import KeyBuilder

logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
P = ParamSpec("P")
R = TypeVar("R")


def _augment_signature(
    signature: inspect.Signature, add_request: bool, add_response: bool
) -> inspect.Signature:
    if not (add_request or add_response):
        return signature

    parameters = list(signature.parameters.values())
    variadic_keyword_params = []
    while parameters and parameters[-1].kind is inspect.Parameter.VAR_KEYWORD:
        variadic_keyword_params.append(parameters.pop())

    if add_request:
        parameters.append(
            inspect.Parameter(
                name="request",
                annotation=Request,
                kind=inspect.Parameter.KEYWORD_ONLY,
            ),
        )
    if add_response:
        parameters.append(
            inspect.Parameter(
                name="response",
                annotation=Response,
                kind=inspect.Parameter.KEYWORD_ONLY,
            ),
        )
    return signature.replace(parameters=[*parameters, *variadic_keyword_params])


def cache(
    expire: Optional[int] = None,
    coder: Optional[Type[Coder]] = None,
    key_builder: Optional[KeyBuilder] = None,
    namespace: Optional[str] = "",
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    cache all function
    :param namespace:
    :param expire:
    :param coder:
    :param key_builder:

    :return:
    """

    def wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        signature = inspect.signature(func)
        request_param = next(
            (param for param in signature.parameters.values() if param.annotation is Request),
            None,
        )
        response_param = next(
            (param for param in signature.parameters.values() if param.annotation is Response),
            None,
        )
        return_type = get_typed_return_annotation(func)

        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal coder
            nonlocal expire
            nonlocal key_builder

            async def ensure_async_func(*args: P.args, **kwargs: P.kwargs) -> R:
                """Run cached sync functions in thread pool just like FastAPI."""
                # if the wrapped function does NOT have request or response in its function signature,
                # make sure we don't pass them in as keyword arguments
                if not request_param:
                    kwargs.pop("request", None)
                if not response_param:
                    kwargs.pop("response", None)

                if inspect.iscoroutinefunction(func):
                    # async, return as is.
                    # unintuitively, we have to await once here, so that caller
                    # does not have to await twice. See
                    # https://stackoverflow.com/a/59268198/532513
                    return await func(*args, **kwargs)
                else:
                    # sync, wrap in thread and return async
                    # see above why we have to await even although caller also awaits.
                    return await run_in_threadpool(func, *args, **kwargs)

            copy_kwargs = kwargs.copy()
            request: Optional[Request] = copy_kwargs.pop("request", None)
            response: Optional[Response] = copy_kwargs.pop("response", None)
            if (
                request and request.headers.get("Cache-Control") in ("no-store", "no-cache")
            ) or not FastAPICache.get_enable():
                return await ensure_async_func(*args, **kwargs)

            coder = coder or FastAPICache.get_coder()
            expire = expire or FastAPICache.get_expire()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()

            cache_key = key_builder(
                func,
                namespace,
                request=request,
                response=response,
                args=args,
                kwargs=copy_kwargs,
            )
            if inspect.isawaitable(cache_key):
                cache_key = await cache_key

            try:
                ttl, ret = await backend.get_with_ttl(cache_key)
            except Exception:
                logger.warning(
                    f"Error retrieving cache key '{cache_key}' from backend:", exc_info=True
                )
                ttl, ret = 0, None
            if not request:
                if ret is not None:
                    return coder.decode_as_type(ret, type_=return_type)
                ret = await ensure_async_func(*args, **kwargs)
                try:
                    await backend.set(cache_key, coder.encode(ret), expire)
                except Exception:
                    logger.warning(
                        f"Error setting cache key '{cache_key}' in backend:", exc_info=True
                    )
                return ret

            if request.method != "GET":
                return await ensure_async_func(*args, **kwargs)

            if_none_match = request.headers.get("if-none-match")
            if ret is not None:
                if response:
                    response.headers["Cache-Control"] = f"max-age={ttl}"
                    etag = f"W/{hash(ret)}"
                    if if_none_match == etag:
                        response.status_code = 304
                        return response
                    response.headers["ETag"] = etag
                return coder.decode_as_type(ret, type_=return_type)

            ret = await ensure_async_func(*args, **kwargs)
            encoded_ret = coder.encode(ret)

            try:
                await backend.set(cache_key, encoded_ret, expire)
            except Exception:
                logger.warning(f"Error setting cache key '{cache_key}' in backend:", exc_info=True)

            response.headers["Cache-Control"] = f"max-age={expire}"
            etag = f"W/{hash(encoded_ret)}"
            response.headers["ETag"] = etag
            return ret

        inner.__signature__ = _augment_signature(
            signature, request_param is None, response_param is None
        )
        return inner

    return wrapper
