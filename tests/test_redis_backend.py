from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from fastapi_cache.backends.redis import RedisBackend


class MockConnectionPool:
    """Mock Redis connection pool."""

    def __init__(self) -> None:
        self.connection_kwargs: Dict[str, Any] = {}


class MockRedisClient:
    """Mock Redis client."""

    def __init__(self, has_pool: bool = True) -> None:
        self.connection_pool: Optional[MockConnectionPool] = (
            MockConnectionPool() if has_pool else None
        )


@pytest.fixture
def mock_redis_client() -> MockRedisClient:
    """Create a mock Redis client with connection pool."""
    return MockRedisClient(has_pool=True)


@pytest.fixture
def mock_redis_client_no_pool() -> MockRedisClient:
    """Create a mock Redis client without connection pool."""
    return MockRedisClient(has_pool=False)


def test_add_driver_info_with_driver_info_class(mock_redis_client: MockRedisClient) -> None:
    """Test _add_driver_info when DriverInfo class is available."""
    mock_driver_info_instance = MagicMock()
    mock_driver_info_instance.add_upstream_driver.return_value = mock_driver_info_instance
    mock_driver_info_class = MagicMock(return_value=mock_driver_info_instance)

    with patch("redis.DriverInfo", mock_driver_info_class, create=True):
        with patch("fastapi_cache.__version__", "0.2.2"):
            RedisBackend(mock_redis_client)  # type: ignore[arg-type]

            # Verify DriverInfo was instantiated
            mock_driver_info_class.assert_called_once()
            mock_driver_info_instance.add_upstream_driver.assert_called_once_with(
                "fastapi-cache", "0.2.2"
            )

            # Verify driver_info was set in connection_kwargs
            assert "driver_info" in mock_redis_client.connection_pool.connection_kwargs  # type: ignore[union-attr]
            assert (
                mock_redis_client.connection_pool.connection_kwargs["driver_info"]  # type: ignore[union-attr]
                == mock_driver_info_instance
            )


def test_add_driver_info_fallback_without_driver_info(
    mock_redis_client: MockRedisClient,
) -> None:
    """Test _add_driver_info fallback when DriverInfo is not available."""
    with patch("redis.DriverInfo", side_effect=ImportError, create=True):
        with patch("fastapi_cache.__version__", "0.2.2"):
            with patch("redis.__version__", "5.0.0"):
                RedisBackend(mock_redis_client)  # type: ignore[arg-type]

                # Verify fallback to lib_name/lib_version
                assert "lib_name" in mock_redis_client.connection_pool.connection_kwargs  # type: ignore[union-attr]
                assert "lib_version" in mock_redis_client.connection_pool.connection_kwargs  # type: ignore[union-attr]

                lib_name = mock_redis_client.connection_pool.connection_kwargs["lib_name"]  # type: ignore[union-attr]
                assert lib_name == "redis-py(fastapi-cache_v0.2.2)"
                assert (
                    mock_redis_client.connection_pool.connection_kwargs["lib_version"]  # type: ignore[union-attr]
                    == "5.0.0"
                )


def test_add_driver_info_fallback_unknown_redis_version(
    mock_redis_client: MockRedisClient,
) -> None:
    """Test _add_driver_info fallback when redis version is unknown."""
    with patch("redis.DriverInfo", side_effect=ImportError, create=True):
        with patch("fastapi_cache.__version__", "0.2.2"):
            # Delete __version__ from redis module to trigger AttributeError
            import redis
            original_version = getattr(redis, "__version__", None)
            try:
                if hasattr(redis, "__version__"):
                    delattr(redis, "__version__")

                RedisBackend(mock_redis_client)  # type: ignore[arg-type]

                # Verify fallback with unknown version
                assert "lib_version" in mock_redis_client.connection_pool.connection_kwargs  # type: ignore[union-attr]
                assert (
                    mock_redis_client.connection_pool.connection_kwargs["lib_version"]  # type: ignore[union-attr]
                    == "unknown"
                )
            finally:
                # Restore original version
                if original_version is not None:
                    redis.__version__ = original_version  # type: ignore[attr-defined]


def test_add_driver_info_no_connection_pool(
    mock_redis_client_no_pool: MockRedisClient,
) -> None:
    """Test _add_driver_info when connection pool is not available."""
    # Should not raise an error, just return early
    backend = RedisBackend(mock_redis_client_no_pool)  # type: ignore[arg-type]

    # Verify no error was raised and backend was created
    assert backend.redis == mock_redis_client_no_pool


def test_add_driver_info_attribute_error_fallback(
    mock_redis_client: MockRedisClient,
) -> None:
    """Test _add_driver_info fallback when DriverInfo raises AttributeError."""
    with patch("redis.DriverInfo", side_effect=AttributeError, create=True):
        with patch("fastapi_cache.__version__", "0.2.2"):
            with patch("redis.__version__", "4.5.0"):
                RedisBackend(mock_redis_client)  # type: ignore[arg-type]

                # Verify fallback to lib_name/lib_version
                assert "lib_name" in mock_redis_client.connection_pool.connection_kwargs  # type: ignore[union-attr]
                assert (
                    mock_redis_client.connection_pool.connection_kwargs["lib_version"]  # type: ignore[union-attr]
                    == "4.5.0"
                )


def test_redis_backend_is_cluster_false(mock_redis_client: MockRedisClient) -> None:
    """Test that is_cluster is False for regular Redis client."""
    backend = RedisBackend(mock_redis_client)  # type: ignore[arg-type]
    assert backend.is_cluster is False


def test_redis_backend_initialization(mock_redis_client: MockRedisClient) -> None:
    """Test RedisBackend initialization."""
    backend = RedisBackend(mock_redis_client)  # type: ignore[arg-type]

    assert backend.redis == mock_redis_client
    assert backend.is_cluster is False

