import json
import pickle  # nosec:B403
from typing import Any


class Coder:
    @classmethod
    def encode(cls, value: Any):
        raise NotImplementedError

    @classmethod
    def decode(cls, value: Any):
        raise NotImplementedError


class JsonCoder(Coder):
    @classmethod
    def encode(cls, value: Any):
        return json.dumps(value)

    @classmethod
    def decode(cls, value: Any):
        return json.loads(value)


class PickleCoder(Coder):
    @classmethod
    def encode(cls, value: Any):
        return pickle.dumps(value)

    @classmethod
    def decode(cls, value: Any):
        return pickle.loads(value)  # nosec:B403
