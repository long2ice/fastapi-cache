import inspect
import sys
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar
if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder
from fastapi_cache.utils import async_partial

P = ParamSpec("P")
R = TypeVar("R")


def cache(
    expire: Optional[int] = None,
    coder: Optional[Coder] = None,
    key_builder: Optional[Callable[..., Any]] = None,
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
        parameters = [*signature.parameters.values()]
        if not request_param:
            parameters.append(
                inspect.Parameter(
                    name="request",
                    annotation=Request,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            )
        if not response_param:
            parameters.append(
                inspect.Parameter(
                    name="response",
                    annotation=Response,
                    kind=inspect.Parameter.KEYWORD_ONLY,
                ),
            )
        if parameters:
            signature = signature.replace(parameters=parameters)
        func.__signature__ = signature

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
                    kwargs.pop("request")
                if not response_param:
                    kwargs.pop("response")

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
            request = copy_kwargs.pop("request", None)
            response = copy_kwargs.pop("response", None)

            if (
                request and request.headers.get("Cache-Control") in ("no-store", "no-cache")
            ) or not FastAPICache.get_enable():
                return await ensure_async_func(*args, **kwargs)

            coder = coder or FastAPICache.get_coder()
            expire = expire or FastAPICache.get_expire()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()

            if inspect.iscoroutinefunction(key_builder):
                cache_key = await key_builder(
                    func,
                    namespace,
                    request=request,
                    response=response,
                    args=args,
                    kwargs=copy_kwargs
                )
            else:
                cache_key = key_builder(
                    func,
                    namespace,
                    request=request,
                    response=response,
                    args=args,
                    kwargs=copy_kwargs
                )

            ttl, ret = await backend.get_with_ttl(cache_key)
            if not request:
                if ret is not None:
                    return coder.decode(ret)
                ret = await ensure_async_func(*args, **kwargs)
                await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
                return ret

            if request.method != "GET":
                return await ensure_async_func(request, *args, **kwargs)

            if_none_match = request.headers.get("if-none-match")
            if ret is not None:
                if response:
                    response.headers["Cache-Control"] = f"max-age={ttl}"
                    etag = f"W/{hash(ret)}"
                    if if_none_match == etag:
                        response.status_code = 304
                        return response
                    response.headers["ETag"] = etag
                return coder.decode(ret)

            ret = await ensure_async_func(*args, **kwargs)

            await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
            return ret

        return inner

    return wrapper


def cacheable(
    expire: Optional[int] = None,
    coder: Optional[Coder] = None,
    key: Optional[str] = None,
    key_builder: Optional[Callable[..., bool]] = None,
    namespace: Optional[str] = "",
    unless: Optional[Callable[..., bool]] = None,
    condition: Optional[Callable[..., bool]] = None,
):
    """Decorator to cache the result of a function.

    e.g.:
        # cache_key depends on the function keyword arguments, not depend on the function position arguments
        @cacheable(expire=60, key="my_key:{user_id}")
        async def get_user(*, user_id: int) -> dict:
            return {"user_id": user_id, "name": "John Doe"}


    :param expire: expire time in seconds
    :param coder: coder, default is JsonCoder
    :param key: cache key, if not set, use default key builder
    :param key_builder: cache key builder, if not set, use default key builder
    :param namespace: cache namespace
    :param unless: if unless return True, do not cache
    :param condition: if condition return True, cache.
    """

    def wrapper(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal coder
            nonlocal expire
            nonlocal key_builder
            nonlocal unless
            nonlocal condition

            coder = coder or FastAPICache.get_coder()
            expire = expire or FastAPICache.get_expire()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()

            if key:
                cache_key = key.format(*args, **kwargs)
            else:
                cache_key = await async_partial(key_builder)(
                    func,
                    namespace,
                    args=args,
                    kwargs=kwargs.copy()
                )

            ttl, cache_ret = await backend.get_with_ttl(cache_key)
            if cache_ret is not None:
                return coder.decode(cache_ret)
            ret = await async_partial(func)(*args, **kwargs)
            if unless and await async_partial(unless)(*args, **kwargs, ret=ret):
                return ret
            if condition is None:
                condition = lambda *a, **kw: bool(ret)
            if await async_partial(condition)(*args, **kwargs, ret=ret):
                await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
            return ret

        return inner

    return wrapper
