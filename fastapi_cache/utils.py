import inspect
from functools import wraps
from typing import Any, Callable, Coroutine, ParamSpec, TypeVar

from starlette.concurrency import run_in_threadpool

P = ParamSpec("P")
R = TypeVar("R")


def async_partial(call: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    @wraps(call)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if inspect.iscoroutinefunction(call):
            return await call(*args, **kwargs)
        else:
            return await run_in_threadpool(call, *args, **kwargs)
    return wrapper


def default_condition(*args: tuple, ret: Any, **kwargs: dict) -> bool:
    return bool(ret)
