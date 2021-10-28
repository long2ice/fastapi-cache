from functools import wraps
from typing import Callable, Optional, Type

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder


def cache(
    expire: int = None,
    coder: Type[Coder] = None,
    key_builder: Callable = None,
    namespace: Optional[str] = "",
):
    """
    cache all function
    :param namespace:
    :param expire:
    :param coder:
    :param key_builder:
    :return:
    """

    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            nonlocal coder
            nonlocal expire
            nonlocal key_builder
            copy_kwargs = kwargs.copy()
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

            ret = await func(*args, **kwargs)
            await backend.set(cache_key, coder.encode(ret), expire or FastAPICache.get_expire())
            return ret

        return inner

    return wrapper
