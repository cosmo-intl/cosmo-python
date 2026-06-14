"""Exception types raised by :mod:`cosmo`."""


class CosmoError(Exception):
    """Base error for cosmo. Catch this to handle any library error;
    catch a subclass to distinguish the cause."""


class InvalidArgumentError(CosmoError, ValueError):
    """A caller passed an invalid argument — a typo'd option key, an unknown
    currency code, an unsupported width/unit, a bad enum value, …

    Also a :class:`ValueError`, so existing ``except ValueError`` handlers catch it.
    """


class UnsupportedError(CosmoError):
    """The underlying ICU/PyICU build exposes no binding for the requested
    operation (e.g. enumerating currencies). Environmental, not a caller bug."""
