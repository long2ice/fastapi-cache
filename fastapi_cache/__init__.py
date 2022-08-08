from typing import Callable

from fastapi_cache.coder import Coder, JsonCoder
from fastapi_cache.key_builder import default_key_builder


class FastAPICache:
    _backend = None
    _prefix = None
    _expire = None
    _init = False
    _coder = None
    _key_builder = None
    _enable = True

    @classmethod
    def init(
        cls,
        backend,
        prefix: str = "",
        expire: int = None,
        coder: Coder = JsonCoder,
        key_builder: Callable = default_key_builder,
        enable: bool = True,
    ):
        if cls._init:
            return
        cls._init = True
        cls._backend = backend
        cls._prefix = prefix
        cls._expire = expire
        cls._coder = coder
        cls._key_builder = key_builder
        cls._enable = enable

    @classmethod
    def get_backend(cls):
        assert cls._backend, "You must call init first!"  # nosec: B101
        return cls._backend

    @classmethod
    def get_prefix(cls):
        return cls._prefix

    @classmethod
    def get_expire(cls):
        return cls._expire

    @classmethod
    def get_coder(cls):
        return cls._coder

    @classmethod
    def get_key_builder(cls):
        return cls._key_builder

    @classmethod
    def get_enable(cls):
        return cls._enable

    @classmethod
    async def clear(cls, namespace: str = None, key: str = None):
        namespace = cls._prefix + ":" + namespace if namespace else None
        return await cls._backend.clear(namespace, key)
