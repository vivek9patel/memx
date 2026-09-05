class MemxError(Exception):
    """Base exception for all memx errors."""


class AdapterError(MemxError):
    """Raised when an adapter fails to ingest, query, or export state."""


class AdapterNotImplementedError(AdapterError, NotImplementedError):
    """Raised when an adapter subclass omits a required method."""


class AdapterTimeoutError(AdapterError):
    """Raised when wait_until_ready() exceeds its timeout."""
