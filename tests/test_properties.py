"""Property-based tests for fastapi-cache2.

Uses Hypothesis for property-based testing and fakeredis for an in-memory
async Redis implementation.
"""

import datetime

import fakeredis
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.coder import JsonCoder


# Feature: redis5-prefect-compatibility, Property 1: Redis Backend round-trip preservation
# **Validates: Requirements 1.2, 1.3, 8.3, 8.4**
@settings(max_examples=100)
@given(
    key=st.text(min_size=1),
    value=st.binary(min_size=1),
)
@pytest.mark.asyncio
async def test_redis_backend_roundtrip(key: str, value: bytes) -> None:
    """For any valid key and value, set followed by get returns the original value."""
    redis = fakeredis.FakeAsyncRedis()
    backend = RedisBackend(redis)

    await backend.set(key, value)
    result = await backend.get(key)

    assert result == value

    await redis.aclose()  # type: ignore[attr-defined]


# Feature: redis5-prefect-compatibility, Property 2: TTL consistency after set
# **Validates: Requirements 1.4, 8.2**
@settings(max_examples=100)
@given(
    key=st.text(min_size=1),
    value=st.binary(min_size=1),
    ttl=st.integers(min_value=1, max_value=86400),
)
@pytest.mark.asyncio
async def test_ttl_consistency_after_set(
    key: str, value: bytes, ttl: int
) -> None:
    """For any valid key, value, and TTL, get_with_ttl returns a positive TTL <= original and matching value."""
    redis = fakeredis.FakeAsyncRedis()
    backend = RedisBackend(redis)

    await backend.set(key, value, expire=ttl)
    returned_ttl, returned_value = await backend.get_with_ttl(key)

    assert returned_ttl > 0
    assert returned_ttl <= ttl
    assert returned_value == value

    await redis.aclose()  # type: ignore[attr-defined]


# Feature: redis5-prefect-compatibility, Property 4: JsonCoder datetime round-trip
# **Validates: Requirements 3.2**
@settings(max_examples=100)
@given(dt=st.datetimes(timezones=st.timezones()))
def test_jsoncoder_datetime_roundtrip(dt: datetime.datetime) -> None:
    """For any valid datetime, encode then decode preserves date/time components."""
    # Filter out datetimes where the timezone's utcoffset has non-zero seconds
    # (pendulum can't handle historical timezone quirks)
    offset = dt.utcoffset()
    if offset is not None:
        assume(offset.total_seconds() % 60 == 0)

    encoded = JsonCoder.encode(dt)
    decoded = JsonCoder.decode(encoded)

    assert decoded.year == dt.year
    assert decoded.month == dt.month
    assert decoded.day == dt.day
    assert decoded.hour == dt.hour
    assert decoded.minute == dt.minute
    assert decoded.second == dt.second


@settings(max_examples=100)
@given(d=st.dates())
def test_jsoncoder_date_roundtrip(d: datetime.date) -> None:
    """For any valid date, encode then decode preserves year, month, day."""
    encoded = JsonCoder.encode(d)
    decoded = JsonCoder.decode(encoded)

    assert decoded.year == d.year
    assert decoded.month == d.month
    assert decoded.day == d.day


# Feature: redis5-prefect-compatibility, Property 3: Clear by namespace removes only matching keys
# **Validates: Requirements 8.5**
@settings(max_examples=100)
@given(
    namespace=st.text(
        min_size=1,
        alphabet=st.characters(whitelist_categories=("L", "N")),
    ),
    ns_keys=st.lists(
        st.text(
            min_size=1, alphabet=st.characters(whitelist_categories=("L", "N"))
        ),
        min_size=1,
        max_size=5,
    ),
    other_keys=st.lists(
        st.text(
            min_size=1, alphabet=st.characters(whitelist_categories=("L", "N"))
        ),
        min_size=1,
        max_size=5,
    ),
)
@pytest.mark.asyncio
async def test_clear_namespace_isolation(
    namespace: str, ns_keys: list[str], other_keys: list[str]
) -> None:
    """Clearing by namespace removes only keys matching {namespace}:* and leaves others intact."""
    # Ensure other_keys don't accidentally start with the namespace prefix
    other_keys = [k for k in other_keys if not k.startswith(f"{namespace}:")]
    assume(len(other_keys) > 0)

    redis = fakeredis.FakeAsyncRedis()
    backend = RedisBackend(redis)

    # Store values under namespace-prefixed keys
    ns_value = b"namespaced_value"
    for key in ns_keys:
        await backend.set(f"{namespace}:{key}", ns_value)

    # Store values under non-namespace keys
    other_value = b"other_value"
    for key in other_keys:
        await backend.set(key, other_value)

    # Clear by namespace
    await backend.clear(namespace=namespace)

    # All namespace-prefixed keys should be gone
    for key in ns_keys:
        result = await backend.get(f"{namespace}:{key}")
        assert result is None, f"Expected {namespace}:{key} to be deleted"

    # All other keys should still have their values
    for key in other_keys:
        result = await backend.get(key)
        assert result == other_value, f"Expected {key} to still have its value"

    await redis.aclose()  # type: ignore[attr-defined]


# Feature: redis5-prefect-compatibility, Property 5: Clear with no arguments is a no-op
# **Validates: Requirements 8.5**
@settings(max_examples=100)
@given(
    keys=st.lists(
        st.text(
            min_size=1, alphabet=st.characters(whitelist_categories=("L", "N"))
        ),
        min_size=1,
        max_size=10,
        unique=True,
    ),
    values=st.lists(
        st.binary(min_size=1),
        min_size=1,
        max_size=10,
    ),
)
@pytest.mark.asyncio
async def test_clear_no_args_is_noop(
    keys: list[str], values: list[bytes]
) -> None:
    """Calling clear(namespace=None, key=None) returns 0 and leaves all keys intact."""
    # Match lengths by trimming the longer list
    size = min(len(keys), len(values))
    keys = keys[:size]
    values = values[:size]

    redis = fakeredis.FakeAsyncRedis()
    backend = RedisBackend(redis)

    # Store key-value pairs
    for key, value in zip(keys, values, strict=False):
        await backend.set(key, value)

    # Call clear with no arguments (defaults to namespace=None, key=None)
    result = await backend.clear()

    # Should return 0
    assert result == 0

    # All pre-existing keys should still be accessible with their original values
    for key, value in zip(keys, values, strict=False):
        stored = await backend.get(key)
        assert stored == value, (
            f"Expected key '{key}' to still have value {value!r}, got {stored!r}"
        )

    await redis.aclose()  # type: ignore[attr-defined]
