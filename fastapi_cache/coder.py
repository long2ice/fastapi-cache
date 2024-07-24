import datetime
import json
import pickle  # nosec:B403
from decimal import Decimal
from typing import Any, Callable, ClassVar, Dict, Optional, TypeVar, Union, overload

import pendulum
from fastapi.encoders import jsonable_encoder
from pydantic import create_model
from pydantic._internal._model_construction import ModelMetaclass
from starlette.responses import JSONResponse
from starlette.templating import (
    _TemplateResponse as TemplateResponse,  # pyright: ignore[reportPrivateUsage]
)

_T = TypeVar("_T", bound=type)


CONVERTERS: Dict[str, Callable[[str], Any]] = {
    # Pendulum 3.0.0 adds parse to __all__, at which point these ignores can be removed
    "date": lambda x: pendulum.parse(x, exact=True),  # type: ignore[attr-defined]
    "datetime": lambda x: pendulum.parse(x, exact=True),  # type: ignore[attr-defined]
    "decimal": Decimal,
}


class JsonEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime.datetime):
            return {"val": str(o), "_spec_type": "datetime"}
        elif isinstance(o, datetime.date):
            return {"val": str(o), "_spec_type": "date"}
        elif isinstance(o, Decimal):
            return {"val": str(o), "_spec_type": "decimal"}
        else:
            return jsonable_encoder(o)


def object_hook(obj: Any) -> Any:
    _spec_type = obj.get("_spec_type")
    if not _spec_type:
        return obj

    if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj["val"])
    else:
        raise TypeError(f"Unknown {_spec_type}")


class Coder:
    @classmethod
    def encode(cls, value: Any) -> bytes:
        raise NotImplementedError

    @classmethod
    def decode(cls, value: bytes) -> Any:
        raise NotImplementedError

    _type_field_cache: ClassVar[Dict[Any, ModelMetaclass]] = {}

    @overload
    @classmethod
    def decode_as_type(cls, value: bytes, *, type_: _T) -> _T:
        ...

    @overload
    @classmethod
    def decode_as_type(cls, value: bytes, *, type_: None) -> Any:
        ...

    @classmethod
    def decode_as_type(cls, value: bytes, *, type_: Optional[_T]) -> Union[_T, Any]:
        """Decode value to the specific given type

        The default implementation uses the Pydantic model system to convert the value.

        """
        result = cls.decode(value)

        if type_ is not None:
            try:
                ModelField = cls._type_field_cache[type_]
            except KeyError:
                ModelField = create_model(
                    'ModelField', value=(type_, ...)
                )
                cls._type_field_cache[type_] = ModelField

            return ModelField.construct(value=result).value # type: ignore

        return result


class JsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        if isinstance(value, JSONResponse):
            return value.body
        return json.dumps(value, cls=JsonEncoder).encode()

    @classmethod
    def decode(cls, value: bytes) -> Any:
        # explicitly decode from UTF-8 bytes first, as otherwise
        # json.loads() will first have to detect the correct UTF-
        # encoding used.
        return json.loads(value.decode(), object_hook=object_hook)


class PickleCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> bytes:
        if isinstance(value, TemplateResponse):
            value = value.body
        return pickle.dumps(value)

    @classmethod
    def decode(cls, value: bytes) -> Any:
        return pickle.loads(value)  # noqa: S301

    @classmethod
    def decode_as_type(cls, value: bytes, *, type_: Optional[_T]) -> Any:
        # Pickle already produces the correct type on decoding, no point
        # in paying an extra performance penalty for pydantic to discover
        # the same.
        return cls.decode(value)
