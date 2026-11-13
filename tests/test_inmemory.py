import asyncio
from typing import Generator, Optional

import pytest

from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache


@pytest.fixture(autouse=True)
def _reset_cache() -> Generator[None, None, None]:
    FastAPICache.reset()
    InMemoryBackend._store.clear()
    yield
    FastAPICache.reset()
    InMemoryBackend._store.clear()


@pytest.mark.parametrize(
    ("namespace", "retained_key"),
    [
        ("app:user", "app:users:one"),
        ("app:user", "app:username:one"),
        ("app:user", "app:user"),
        ("app:user", "app:user-two:one"),
        ("app", "application:user:one"),
        ("app", "app-two:user:one"),
        ("app:user:child", "app:user:children:one"),
        ("app:user", "other:user:one"),
    ],
)
def test_clear_namespace_respects_boundary(namespace: str, retained_key: str) -> None:
    async def run() -> None:
        backend = InMemoryBackend()
        target_key = namespace + ":one"
        child_key = namespace + ":child:one"
        await backend.set(target_key, b"target", expire=60)
        await backend.set(child_key, b"child", expire=60)
        await backend.set(retained_key, b"retained", expire=60)

        assert await backend.clear(namespace=namespace) == 2
        assert await backend.get(target_key) is None
        assert await backend.get(child_key) is None
        assert await backend.get(retained_key) == b"retained"
        assert await backend.clear(namespace=namespace) == 0

    asyncio.run(run())


@pytest.mark.parametrize("namespace", [None, "user"])
def test_clear_preserves_other_decorated_namespaces(namespace: Optional[str]) -> None:
    async def run() -> None:
        backend = InMemoryBackend()
        FastAPICache.init(backend, prefix="app")
        calls = {"target": 0, "sibling": 0}

        @cache(expire=60, namespace="user")
        async def target() -> int:
            calls["target"] += 1
            return calls["target"]

        @cache(expire=60, namespace="users")
        async def sibling() -> int:
            calls["sibling"] += 1
            return calls["sibling"]

        assert await target() == 1
        assert await sibling() == 1
        assert await target() == 1
        assert await sibling() == 1
        if namespace is None:
            # Clearing an application's whole prefix must not clear another
            # application with a longer prefix in the shared in-memory store.
            await backend.set("application:user:one", b"other", expire=60)
            assert await FastAPICache.clear() == 2
            assert await backend.get("application:user:one") == b"other"
            assert await target() == 2
            assert await sibling() == 2
        else:
            assert await FastAPICache.clear(namespace=namespace) == 1
            assert await target() == 2
            assert await sibling() == 1

    asyncio.run(run())


def test_clear_by_key_does_not_clear_related_keys() -> None:
    async def run() -> None:
        backend = InMemoryBackend()
        await backend.set("app:user:one", b"one", expire=60)
        await backend.set("app:user:one:child", b"child", expire=60)
        assert await backend.clear(key="app:user:one") == 1
        assert await backend.get("app:user:one") is None
        assert await backend.get("app:user:one:child") == b"child"

    asyncio.run(run())


def test_clear_without_arguments_remains_a_noop() -> None:
    async def run() -> None:
        backend = InMemoryBackend()
        await backend.set("app:user:one", b"one", expire=60)
        assert await backend.clear() == 0
        assert await backend.get("app:user:one") == b"one"

    asyncio.run(run())
