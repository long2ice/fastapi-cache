class FastAPICache:
    _backend = None
    _prefix = None
    _expire = None
    _init = False

    @classmethod
    def init(cls, backend, prefix: str = "", expire: int = None):
        if cls._init:
            return
        cls._init = True
        cls._backend = backend
        cls._prefix = prefix
        cls._expire = expire

    @classmethod
    def get_backend(cls):
        assert cls._backend, "You must call init first!"  # nosec: B101
        return cls._backend

    @classmethod
    def get_prefix(cls):
        return cls._prefix

    @classmethod
    def get_expire(cls):
        return cls._expire
