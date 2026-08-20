import logging
import sys
from functools import wraps
from inspect import Parameter, Signature, isawaitable, iscoroutinefunction
from typing import (
    Any,
    Awaitable,
    Callable,
    Collection,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

from fastapi.concurrency import run_in_threadpool
from fastapi.dependencies.utils import (
    get_typed_return_annotation,
    get_typed_signature,
)
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_304_NOT_MODIFIED

from fastapi_cache import FastAPICache
from fastapi_cache.coder import Coder
from fastapi_cache.types import KeyBuilder

logger: logging.Logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
P = ParamSpec("P")
R = TypeVar("R")


def _augment_signature(signature: Signature, *extra: Parameter) -> Signature:
    if not extra:
        return signature

    parameters = list(signature.parameters.values())
    variadic_keyword_params: List[Parameter] = []
    while parameters and parameters[-1].kind is Parameter.VAR_KEYWORD:
        variadic_keyword_params.append(parameters.pop())

    return signature.replace(parameters=[*parameters, *extra, *variadic_keyword_params])


def _locate_param(
    sig: Signature, dep: Parameter, to_inject: List[Parameter]
) -> Parameter:
    """Locate an existing parameter in the decorated endpoint

    If not found, returns the injectable parameter, and adds it to the to_inject list.

    """
    param = next(
        (p for p in sig.parameters.values() if p.annotation is dep.annotation), None
    )
    if param is None:
        to_inject.append(dep)
        param = dep
    return param


def _check_excluded_params(sig: Signature, exclude_params: Collection[str]) -> None:
    """Verify that the excluded parameter names exist on the decorated function

    Functions accepting arbitrary keyword arguments are exempt, as any name
    could be a valid argument for those.

    """
    if any(p.kind is Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return
    unknown = sorted(set(exclude_params) - set(sig.parameters))
    if unknown:
        raise ValueError(
            f"exclude_params contains parameters not present in the signature: "
            f"{', '.join(unknown)}"
        )


def _exclude_params(
    sig: Signature,
    exclude_params: Collection[str],
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> Tuple[Tuple[Any, ...], Dict[str, Any]]:
    """Drop the named parameters from the arguments used to build the cache key

    Arguments passed positionally are matched to their parameter name by
    position; anything absorbed by a variadic positional parameter is kept.

    """
    filtered_kwargs = {k: v for k, v in kwargs.items() if k not in exclude_params}
    if not args:
        return args, filtered_kwargs

    positional = [
        p.name
        for p in sig.parameters.values()
        if p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
    ]
    filtered_args = tuple(
        value
        for i, value in enumerate(args)
        if i >= len(positional) or positional[i] not in exclude_params
    )
    return filtered_args, filtered_kwargs


def _uncacheable(request: Optional[Request]) -> bool:
    """Determine if this request should not be cached

    Returns true if:
    - Caching has been disabled globally
    - This is not a GET request
    - The request has a Cache-Control header with a value of "no-store"

    """
    if not FastAPICache.get_enable():
        return True
    if request is None:
        return False
    if request.method != "GET":
        return True
    return request.headers.get("Cache-Control") == "no-store"


def cache(
    expire: Optional[int] = None,
    coder: Optional[Type[Coder]] = None,
    key_builder: Optional[KeyBuilder] = None,
    namespace: str = "",
    injected_dependency_namespace: str = "__fastapi_cache",
    exclude_params: Optional[Collection[str]] = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[Union[R, Response]]]]:
    """
    cache all function
    :param injected_dependency_namespace:
    :param namespace:
    :param expire:
    :param coder:
    :param key_builder:
    :param exclude_params: names of parameters to leave out of the cache key, so
        that calls differing only in those values share a cache entry. Applied
        before the key builder runs, so it works with custom key builders too.

    :return:
    """

    injected_request = Parameter(
        name=f"{injected_dependency_namespace}_request",
        annotation=Request,
        kind=Parameter.KEYWORD_ONLY,
    )
    injected_response = Parameter(
        name=f"{injected_dependency_namespace}_response",
        annotation=Response,
        kind=Parameter.KEYWORD_ONLY,
    )

    def wrapper(
        func: Callable[P, Awaitable[R]]
    ) -> Callable[P, Awaitable[Union[R, Response]]]:
        # get_typed_signature ensures that any forward references are resolved first
        wrapped_signature = get_typed_signature(func)
        to_inject: List[Parameter] = []
        request_param = _locate_param(wrapped_signature, injected_request, to_inject)
        response_param = _locate_param(wrapped_signature, injected_response, to_inject)
        return_type = get_typed_return_annotation(func)
        if exclude_params:
            _check_excluded_params(wrapped_signature, exclude_params)

        @wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> Union[R, Response]:
            nonlocal coder
            nonlocal expire
            nonlocal key_builder

            async def ensure_async_func(*args: P.args, **kwargs: P.kwargs) -> R:
                """Run cached sync functions in thread pool just like FastAPI."""
                # if the wrapped function does NOT have request or response in
                # its function signature, make sure we don't pass them in as
                # keyword arguments
                kwargs.pop(injected_request.name, None)
                kwargs.pop(injected_response.name, None)

                if iscoroutinefunction(func):
                    # async, return as is.
                    # unintuitively, we have to await once here, so that caller
                    # does not have to await twice. See
                    # https://stackoverflow.com/a/59268198/532513
                    return await func(*args, **kwargs)
                else:
                    # sync, wrap in thread and return async
                    # see above why we have to await even although caller also awaits.
                    return await run_in_threadpool(func, *args, **kwargs)  # type: ignore[arg-type]

            copy_kwargs = kwargs.copy()
            request: Optional[Request] = copy_kwargs.pop(request_param.name, None)  # type: ignore[assignment]
            response: Optional[Response] = copy_kwargs.pop(response_param.name, None)  # type: ignore[assignment]

            if _uncacheable(request):
                return await ensure_async_func(*args, **kwargs)

            prefix = FastAPICache.get_prefix()
            coder = coder or FastAPICache.get_coder()
            expire = expire or FastAPICache.get_expire()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()
            cache_status_header = FastAPICache.get_cache_status_header()

            key_args: Tuple[Any, ...] = args
            key_kwargs: Dict[str, Any] = copy_kwargs
            if exclude_params:
                key_args, key_kwargs = _exclude_params(
                    wrapped_signature, exclude_params, args, copy_kwargs
                )

            cache_key = key_builder(
                func,
                f"{prefix}:{namespace}",
                request=request,
                response=response,
                args=key_args,
                kwargs=key_kwargs,
            )
            if isawaitable(cache_key):
                cache_key = await cache_key
            assert isinstance(cache_key, str)  # noqa: S101  # assertion is a type guard

            try:
                ttl, cached = await backend.get_with_ttl(cache_key)
            except Exception:
                logger.warning(
                    f"Error retrieving cache key '{cache_key}' from backend:",
                    exc_info=True,
                )
                ttl, cached = 0, None

            if cached is None  or (request is not None and request.headers.get("Cache-Control") == "no-cache") :  # cache miss
                result = await ensure_async_func(*args, **kwargs)
                to_cache = coder.encode(result)

                try:
                    await backend.set(cache_key, to_cache, expire)
                except Exception:
                    logger.warning(
                        f"Error setting cache key '{cache_key}' in backend:",
                        exc_info=True,
                    )

                if response:
                    response.headers.update(
                        {
                            "Cache-Control": f"max-age={expire}",
                            "ETag": f"W/{hash(to_cache)}",
                            cache_status_header: "MISS",
                        }
                    )

            else:  # cache hit
                if response:
                    etag = f"W/{hash(cached)}"
                    response.headers.update(
                        {
                            "Cache-Control": f"max-age={ttl}",
                            "ETag": etag,
                            cache_status_header: "HIT",
                        }
                    )

                    if_none_match = request and request.headers.get("if-none-match")
                    if if_none_match == etag:
                        response.status_code = HTTP_304_NOT_MODIFIED
                        return response

                result = cast(R, coder.decode_as_type(cached, type_=return_type))

            return result

        inner.__signature__ = _augment_signature(wrapped_signature, *to_inject)  # type: ignore[attr-defined]

        return inner

    return wrapper
