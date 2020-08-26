class FastAPICache:
    _backend = None
    _prefix = None

    @classmethod
    def init(cls, backend, prefix: str = ""):
        cls._backend = backend
        cls._prefix = prefix

    @classmethod
    def get_backend(cls):
        assert cls._backend, "You must call init first!"  # nosec: B101
        return cls._backend

    @classmethod
    def get_prefix(cls):
        assert cls._prefix, "You must call init first!"  # nosec: B101
        return cls._prefix
