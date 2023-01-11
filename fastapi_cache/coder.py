import codecs
import datetime
import json
import pickle  # nosec:B403
from decimal import Decimal
from typing import Any

import pendulum
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from starlette.templating import _TemplateResponse as TemplateResponse

CONVERTERS = {
    "date": lambda x: pendulum.parse(x, exact=True),
    "datetime": lambda x: pendulum.parse(x, exact=True),
    "decimal": Decimal,
}


class JsonEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime.datetime):
            return {"val": str(obj), "_spec_type": "datetime"}
        elif isinstance(obj, datetime.date):
            return {"val": str(obj), "_spec_type": "date"}
        elif isinstance(obj, Decimal):
            return {"val": str(obj), "_spec_type": "decimal"}
        else:
            return jsonable_encoder(obj)


def object_hook(obj: Any) -> Any:
    _spec_type = obj.get("_spec_type")
    if not _spec_type:
        return obj

    if _spec_type in CONVERTERS:
        return CONVERTERS[_spec_type](obj["val"])  # type: ignore
    else:
        raise TypeError("Unknown {}".format(_spec_type))


class Coder:
    @classmethod
    def encode(cls, value: Any) -> str:
        raise NotImplementedError

    @classmethod
    def decode(cls, value: str) -> Any:
        raise NotImplementedError


class JsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> str:
        if isinstance(value, JSONResponse):
            return value.body
        return json.dumps(value, cls=JsonEncoder)

    @classmethod
    def decode(cls, value: str) -> str:
        return json.loads(value, object_hook=object_hook)


class PickleCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> str:
        if isinstance(value, TemplateResponse):
            value = value.body
        return codecs.encode(pickle.dumps(value), "base64").decode()

    @classmethod
    def decode(cls, value: str) -> Any:
        return pickle.loads(codecs.decode(value.encode(), "base64"))  # nosec:B403,B301
