import inspect
from functools import wraps
from typing import Callable, Optional, Type, List

from fastapi.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import Response

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder


def cache(
    expire: int = None,
    coder: Type[Coder] = None,
    key_builder: Callable = None,
    namespace: Optional[str] = "",
    key_builder_exclude_field: Optional[List[str]] = None
):
    """
    cache all function
    :param namespace:
    :param expire:
    :param coder:
    :param key_builder:
    :param key_builder_exclude_field:

    :return:
    """

    def wrapper(func):
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
        async def inner(*args, **kwargs):
            nonlocal coder
            nonlocal expire
            nonlocal key_builder
            copy_kwargs = kwargs.copy()
            if key_builder_exclude_field:
                for key in kwargs.keys():
                    if key in key_builder_exclude_field:
                        copy_kwargs.pop(key)
            request = copy_kwargs.pop("request", None)
            response = copy_kwargs.pop("response", None)
            if (
                request and request.headers.get("Cache-Control") == "no-store"
            ) or not FastAPICache.get_enable():
                return await func(*args, **kwargs)

            coder = coder or FastAPICache.get_coder()
            expire = expire or FastAPICache.get_expire()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()

            cache_key = key_builder(
                func, namespace, request=request, response=response, args=args, kwargs=copy_kwargs
            )
            ttl, ret = await backend.get_with_ttl(cache_key)
            if not request:
                if ret is not None:
                    return coder.decode(ret)
                ret = await func(*args, **kwargs)
                await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
                return ret

            if request.method != "GET":
                return await func(request, *args, **kwargs)
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
            if not request_param:
                kwargs.pop("request")
            if not response_param:
                kwargs.pop("response")
            if inspect.iscoroutinefunction(func):
                ret = await func(*args, **kwargs)
            else:
                ret = await run_in_threadpool(func, *args, **kwargs)

            await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
            return ret

        return inner

    return wrapper
