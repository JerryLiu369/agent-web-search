_HTTP_ERROR = "HTTP"


def http_error(provider: str, status: int, operation: str | None = None) -> str:
    """Return a stable public HTTP error without exposing upstream response data."""
    prefix = f"{provider} {operation}" if operation else provider
    return f"{prefix} {_HTTP_ERROR} {status}"


def exception_error(
    provider: str, exc: BaseException, operation: str | None = None
) -> str:
    """Return a stable public error without exposing the exception message."""
    prefix = f"{provider} {operation}" if operation else provider
    return f"{prefix} {type(exc).__name__}"
