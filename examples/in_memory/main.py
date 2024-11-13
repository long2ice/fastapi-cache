# pyright: reportGeneralTypeIssues=false
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional

import pendulum
import uvicorn
import logging
from fastapi import FastAPI, Query
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)
from fastapi import HTTPException

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    FastAPICache.init(InMemoryBackend())
    yield


def simulate_cache_failure():
    """Simulate cache failure by resetting FastAPICache."""
    FastAPICache.reset()  # Reset cache settings

def invalid_cache(expire: int = 10, namespace: str = "invalid_cache", continue_on_error: bool = True):
    """Decorator to simulate cache failure."""
    print("Invalid cache decorator called", continue_on_error)
    def decorator(func):
        async def wrapper():
            # Get the continue_on_error from kwargs if present (passed from FastAPI route)
            
            # Simulate cache failure by resetting the cache
            simulate_cache_failure()

            try:
                # Initialize cache settings or use defaults
                prefix = FastAPICache.get_prefix() or ""
                coder = FastAPICache.get_coder() or None
                cache_expire = expire if expire is not None else FastAPICache.get_expire()
                key_builder = FastAPICache.get_key_builder() or None
                backend = FastAPICache.get_backend() or None
                cache_status_header = FastAPICache.get_cache_status_header() or None

                # Now execute the original function with cache logic applied
                return await func()
            
            except AssertionError as e:
                logger.error(f"Error initializing cache: {e}")
                
                if continue_on_error:
                    logger.warning("Continuing without caching")
                    return await func()  # Continue without caching
                else:
                    raise HTTPException(status_code=503, detail="Cache initialization failed.")

            except Exception as e:
                logger.critical(f"Critical error initializing cache: {e}")
                raise HTTPException(status_code=503, detail=f"Cache failure: {str(e)}")

        # Apply the cache decorator with the provided parameters (expire and namespace)
        return cache(expire=expire, namespace=namespace, continue_on_error=continue_on_error)(wrapper)
    
    return decorator


def cache_failure_example(expire: int = 5, namespace: str = "test_namespace", continue_on_error: bool = False):
    # Apply the decorator with dynamic values for the parameters
    @invalid_cache(expire=expire, namespace=namespace, continue_on_error=continue_on_error)
    async def inner_cache_failure_example():
        return {"message": "This should simulate a cache failure."}
    
    # Return the decorated function
    return inner_cache_failure_example


app = FastAPI(lifespan=lifespan)

ret = 0


@cache(namespace="test", expire=1)
async def get_ret():
    global ret
    ret = ret + 1
    return ret


@app.get("/")
@cache(namespace="test", expire=10)
async def index():
    return {"ret": await get_ret()}


@app.get("/clear")
async def clear():
    return await FastAPICache.clear(namespace="test")


@app.get("/date")
@cache(namespace="test", expire=10)
async def get_date():
    return pendulum.today()


@app.get("/datetime")
@cache(namespace="test", expire=2)
async def get_datetime(request: Request, response: Response):
    return {"now": pendulum.now()}


@cache(namespace="test")
async def func_kwargs(*unused_args, **kwargs):
    return kwargs


@app.get("/kwargs")
async def get_kwargs(name: str):
    return await func_kwargs(name, name=name)


@app.get("/sync-me")
@cache(namespace="test") # pyright: ignore[reportArgumentType]
def sync_me():
    # as per the fastapi docs, this sync function is wrapped in a thread,
    # thereby converted to async. fastapi-cache does the same.
    return 42


@app.get("/cache_response_obj")
@cache(namespace="test", expire=5)
async def cache_response_obj():
    return JSONResponse({"a": 1})


class SomeClass:
    def __init__(self, value):
        self.value = value

    async def handler_method(self):
        return self.value


# register an instance method as a handler
instance = SomeClass(17)
app.get("/method")(cache(namespace="test")(instance.handler_method))


# cache a Pydantic model instance; the return type annotation is required in this case
class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    tax: Optional[float] = None


@app.get("/pydantic_instance")
@cache(namespace="test", expire=5)
async def pydantic_instance() -> Item:
    return Item(name="Something", description="An instance of a Pydantic model", price=10.5)


put_ret = 0


@app.put("/uncached_put")
@cache(namespace="test", expire=5)
async def uncached_put():
    global put_ret
    put_ret = put_ret + 1
    return {"value": put_ret}

put_ret2 = 0

@app.get("/cached_put")
@cache(namespace="test", expire=5)
async def cached_put():
    global put_ret2
    put_ret2 = put_ret2 + 1
    return {"value": put_ret2}


@app.get("/namespaced_injection")
@cache(namespace="test", expire=5, injected_dependency_namespace="monty_python") # pyright: ignore[reportArgumentType]
def namespaced_injection(
    __fastapi_cache_request: int = 42, __fastapi_cache_response: int = 17
) -> Dict[str, int]:
    return {
        "__fastapi_cache_request": __fastapi_cache_request,
        "__fastapi_cache_response": __fastapi_cache_response,
    }


##############################################CACHE FAILURE SIMULATION##############################################

@app.get("/cache_failure_example")
async def cache_failure_endpoint(
    expire: int = Query(5, ge=1),  # Default expiration is 5 seconds, but must be at least 1 second
    namespace: str = Query("test_namespace"),
    continue_on_error: bool = Query(False)
):
    # Call the dynamically generated function with the specified parameters
    func = cache_failure_example(expire=expire, namespace=namespace, continue_on_error=continue_on_error)
    
    # Execute the function and return the result
    return await func()


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
