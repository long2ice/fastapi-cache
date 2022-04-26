import pytest
from pydantic import BaseModel

from fastapi_cache.decorator import cache


def test_default_key_builder():
    return 1


class MyModel(BaseModel):
    name: str
    age: int


@cache(expire=3600)
async def get_model() -> MyModel:
    return MyModel(name="John", age=30)


@pytest.mark.asyncio
async def test_get_model_returns_a_model():

    # First time, when is not cached, will return whatever the function returns
    assert isinstance(await get_model(), MyModel)

    # Second time, when is cached, will return the cached value, parsing it to a model
    assert isinstance(await get_model(), MyModel)


