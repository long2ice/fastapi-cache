from fastapi_cache.types import Backend
from fastapi_cache.backends import inmemory


__all__ = ["Backend", "inmemory"]

# import each backend in turn and add to __all__. This syntax
# is explicitly supported by type checkers, while more dynamic
# syntax would not be recognised.
try:
    from fastapi_cache.backends import dynamodb
except ImportError:
    pass
else:
    __all__ += ["dynamodb"]

try:
    from fastapi_cache.backends import memcached
except ImportError:
    pass
else:
    __all__ += ["memcached"]

try:
    from fastapi_cache.backends import redis
except ImportError:
    pass
else:
    __all__ += ["redis"]
