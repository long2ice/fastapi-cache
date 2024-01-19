import inspect
import logging
import sys
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, Type, TypeVar
from fastapi.exceptions import HTTPException

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
P = ParamSpec("P")
R = TypeVar("R")


def cache(
    expire: Optional[int] = None,
    coder: Optional[Type[Coder]] = None,
    key_builder: Optional[Callable[..., Any]] = None,
    namespace: Optional[str] = "",
    allow_client_caching: Optional[bool] = False,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """
    cache all function
    :param namespace:
    :param expire:
    :param coder:
    :param key_builder:
    :param allow_client_caching:

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
        parameters = []
        extra_params = []
        for p in signature.parameters.values():
            if p.kind <= inspect.Parameter.KEYWORD_ONLY:
                parameters.append(p)
            else:
                extra_params.append(p)
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
        parameters.extend(extra_params)
        if parameters:
            signature = signature.replace(parameters=parameters)
        func.__signature__ = signature

        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            nonlocal coder
            nonlocal expire
            nonlocal key_builder
            nonlocal allow_client_caching

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
            # Cache-Control: no-store means do not store the result
            # Cache-Control: no-cache means retrieve a fresh result AND store it
            # Cache-Control: no-store and Cache-Control: no-cache are mutually exclusive
            no_store = request and request.headers.get("Cache-Control") in ["no-store"]
            no_cache = request and request.headers.get("Cache-Control") in ["no-cache"]
            if no_store or not FastAPICache.get_enable():
                logger.debug("Cache disabled due to Cache-Control:no-store")
                return await ensure_async_func(*args, **kwargs)
            # Only use a cache for GET requests (no POST/PUT/etc.)
            if request and request.method != "GET":
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
                    kwargs=copy_kwargs,
                )
            else:
                cache_key = key_builder(
                    func,
                    namespace,
                    request=request,
                    response=response,
                    args=args,
                    kwargs=copy_kwargs,
                )

            # if no_cache, ensure a fresh result, otherwise check cache
            cache_hit = False
            ttl = 0
            etag = ""
            if no_cache:
                ret = await ensure_async_func(*args, **kwargs)
            else:
                try:
                    ttl, encoded_ret = await backend.get_with_ttl(cache_key)
                    if encoded_ret is None:
                        logger.debug(f"Cache miss for key '{cache_key}'")
                        ret = await ensure_async_func(*args, **kwargs)
                    else:
                        logger.debug(f"Cache hit for key '{cache_key}'")
                        cache_hit = True
                        ret = coder.decode(encoded_ret)
                        etag = f"W/{hash(encoded_ret)}"

                except Exception:
                    logger.warning(
                        f"Error retrieving cache key '{cache_key}' from backend:", exc_info=True
                    )
                    ret = await ensure_async_func(*args, **kwargs)

            # if we DIDN'T read from cache, then we should store
            if cache_hit is False:
                try:
                    encoded_ret = coder.encode(ret)
                    await backend.set(cache_key, encoded_ret, expire)
                except Exception:
                    logger.warning(
                        f"Error setting cache key '{cache_key}' in backend:", exc_info=True
                    )

            # Now we need to return something. If it's an internal method
            # then no further processing is needed
            if not request:
                return ret

            # Otherwise, we optionally need some headers
            if response:
                if cache_hit:
                    response.headers["Cache-Control"] = f"max-age={ttl}"
                    response.headers["ETag"] = etag
                    response.headers["X-Cache-Hit"] = "True"
                    response.headers["X-Cache-TTL"] = f"{ttl}"
                    # The If-None-Match HTTP request header makes the request
                    # conditional, returning a 304 status if the ETag matches
                    # something in the cache
                    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/If-None-Match
                    if request and etag == request.headers.get("if-none-match"):
                        raise HTTPException(status_code=304, headers={"ETag": etag})
                else:
                    response.headers["Cache-Control"] = f"max-age={expire}"
                    response.headers["ETag"] = f"W/{hash(coder.encode(ret))}"

                # For certain content, we want to handle all caching at the
                # server (e.g. so we can do automatic invalidation) so
                # this flag instructs the client (i.e. Browser/app) not
                # to do any local caching
                if allow_client_caching == False:
                    response.headers["Cache-Control"] = "no-store"

                return ret

        return inner

    return wrapper
