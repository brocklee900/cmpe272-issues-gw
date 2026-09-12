"""
Maps GitHub API errors (and our own validation errors) into a single,
consistent error shape: { error, message, status, details }.
"""
from typing import Optional

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from app.schemas import ErrorResponse


class AppError(Exception):
    """Base class for errors we raise deliberately, with an HTTP status attached."""

    def __init__(self, status: int, error: str, message: str, details: Optional[dict] = None):
        self.status = status
        self.error = error
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, "not_found", message)


class ValidationAppError(AppError):
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(400, "validation_error", message, details)


class UpstreamAuthError(AppError):
    def __init__(self, message: str = "GitHub rejected our credentials"):
        super().__init__(401, "upstream_auth_error", message)


class UpstreamForbiddenError(AppError):
    def __init__(self, message: str = "GitHub denied the request (permissions or rate limit)"):
        super().__init__(403, "upstream_forbidden", message)


class UpstreamRateLimitError(AppError):
    def __init__(self, retry_after: Optional[int] = None):
        details = {"retry_after_seconds": retry_after} if retry_after is not None else None
        super().__init__(429, "rate_limited", "GitHub API rate limit exceeded", details)


class UpstreamUnavailableError(AppError):
    def __init__(self, message: str = "GitHub API is currently unavailable"):
        super().__init__(503, "upstream_unavailable", message)


def map_github_error(resp: httpx.Response) -> AppError:
    """Translate a non-2xx GitHub response into one of our AppError types."""
    status = resp.status_code
    try:
        payload = resp.json()
        gh_message = payload.get("message", "")
    except Exception:
        gh_message = resp.text[:300]

    if status == 401:
        return UpstreamAuthError(f"GitHub auth failed: {gh_message}")
    if status == 403:
        remaining = resp.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            reset = resp.headers.get("X-RateLimit-Reset")
            retry_after = None
            if reset:
                import time

                retry_after = max(0, int(reset) - int(time.time()))
            return UpstreamRateLimitError(retry_after)
        return UpstreamForbiddenError(f"GitHub forbidden: {gh_message}")
    if status == 404:
        return NotFoundError(f"GitHub resource not found: {gh_message}")
    if status == 422:
        details = payload if "payload" in locals() else None
        return ValidationAppError(f"GitHub validation failed: {gh_message}", details=details)
    if status == 429:
        retry_after = resp.headers.get("Retry-After")
        return UpstreamRateLimitError(int(retry_after) if retry_after else None)
    if status >= 500:
        return UpstreamUnavailableError(f"GitHub server error ({status})")

    return AppError(status, "upstream_error", f"Unexpected GitHub error: {gh_message}")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(error=exc.error, message=exc.message, status=exc.status, details=exc.details)
    return JSONResponse(status_code=exc.status, content=body.model_dump(exclude_none=True))
