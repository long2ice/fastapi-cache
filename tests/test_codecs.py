from typing import Any

import pytest

from fastapi_cache.coder import PickleCoder


@pytest.mark.parametrize(
    "value",
    [
        1,
        "some_string",
        (1, 2),
        [1, 2, 3],
        {"some_key": 1, "other_key": 2},
    ],
)
def test_pickle_coder(value: Any) -> None:
    encoded_value = PickleCoder.encode(value)
    assert isinstance(encoded_value, str)
    decoded_value = PickleCoder.decode(encoded_value)
    assert decoded_value == value
