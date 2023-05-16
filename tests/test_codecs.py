from dataclasses import dataclass
from typing import Any, Optional, Tuple, Type

import pytest
from pydantic import BaseModel, ValidationError

from fastapi_cache.coder import JsonCoder, PickleCoder


@dataclass
class DCItem:
    name: str
    price: float
    description: Optional[str] = None
    tax: Optional[float] = None


class PDItem(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    tax: Optional[float] = None


@pytest.mark.parametrize(
    "value",
    [
        1,
        "some_string",
        (1, 2),
        [1, 2, 3],
        {"some_key": 1, "other_key": 2},
        DCItem(name="foo", price=42.0, description="some dataclass item", tax=0.2),
        PDItem(name="foo", price=42.0, description="some pydantic item", tax=0.2),
    ],
)
def test_pickle_coder(value: Any) -> None:
    encoded_value = PickleCoder.encode(value)
    assert isinstance(encoded_value, bytes)
    decoded_value = PickleCoder.decode(encoded_value)
    assert decoded_value == value


@pytest.mark.parametrize(
    ("value", "return_type"),
    [
        (1, None),
        ("some_string", None),
        ((1, 2), Tuple[int, int]),
        ([1, 2, 3], None),
        ({"some_key": 1, "other_key": 2}, None),
        (DCItem(name="foo", price=42.0, description="some dataclass item", tax=0.2), DCItem),
        (PDItem(name="foo", price=42.0, description="some pydantic item", tax=0.2), PDItem),
    ],
)
def test_json_coder(value: Any, return_type: Type[Any]) -> None:
    encoded_value = JsonCoder.encode(value)
    assert isinstance(encoded_value, bytes)
    decoded_value = JsonCoder.decode_as_type(encoded_value, type_=return_type)
    assert decoded_value == value


def test_json_coder_validation_error() -> None:
    invalid = b'{"name": "incomplete"}'
    with pytest.raises(ValidationError):
        JsonCoder.decode_as_type(invalid, type_=PDItem)
