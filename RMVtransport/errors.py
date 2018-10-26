"""Define package errors."""


class RMVtransportError(Exception):
    """General error exception occurred."""

    pass


class RMVtransportApiConnectionError(RMVtransportError):
    """When a connection error is encountered."""

    pass
