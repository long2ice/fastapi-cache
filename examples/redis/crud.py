import time
from fastapi_cache.decorator import cacheable


def custom_condition(*args, **kwargs):
    ret = kwargs.pop("ret")
    return ret.startswith("cache")


def custom_unless(*args, **kwargs):
    ret = kwargs.pop("ret")
    return ret.startswith("no")


class CRUDExample:
    @cacheable(expire=60, key="crud:{_id}")
    async def get(self, *, _id: str) -> str:
        return f"id: {_id}, ts: {time.time()}"

    @cacheable(expire=60, key="crud:{_id}", condition=custom_condition)
    async def get_with_condition(self, _id: str, is_cache: bool = True):
        if is_cache:
            return f"cache_id: {_id}, ts: {time.time()}"
        return f"id: {_id}, ts: {time.time()}"

    @cacheable(expire=60, key="crud:{_id}", unless=custom_unless)
    async def get_with_unless(self, _id: str, is_cache: bool = True):
        if is_cache is False:
            return f"no_cache_id: {_id}, ts: {time.time()}"
        return f"id: {_id}, ts: {time.time()}"

    @cacheable(expire=60, key="crud:{_id}")
    async def get_dict(self, *, _id: str) -> dict:
        return {"id": _id, "ts": time.time()}


crud_example = CRUDExample()

