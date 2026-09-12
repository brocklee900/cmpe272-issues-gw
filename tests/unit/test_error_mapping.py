import httpx

from app.errors import (
    NotFoundError,
    UpstreamAuthError,
    UpstreamForbiddenError,
    UpstreamRateLimitError,
    UpstreamUnavailableError,
    map_github_error,
)


def _resp(status_code: int, json_body: dict | None = None, headers: dict | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://api.github.com/repos/o/r/issues/1")
    return httpx.Response(
        status_code=status_code,
        json=json_body or {"message": "generic error"},
        headers=headers or {},
        request=request,
    )


def test_401_maps_to_upstream_auth_error():
    err = map_github_error(_resp(401, {"message": "Bad credentials"}))
    assert isinstance(err, UpstreamAuthError)
    assert err.status == 401


def test_404_maps_to_not_found_error():
    err = map_github_error(_resp(404, {"message": "Not Found"}))
    assert isinstance(err, NotFoundError)
    assert err.status == 404


def test_403_with_zero_remaining_maps_to_rate_limit():
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "9999999999"}
    err = map_github_error(_resp(403, {"message": "rate limit"}, headers=headers))
    assert isinstance(err, UpstreamRateLimitError)


def test_403_without_rate_limit_maps_to_forbidden():
    err = map_github_error(_resp(403, {"message": "forbidden"}))
    assert isinstance(err, UpstreamForbiddenError)


def test_429_maps_to_rate_limit_with_retry_after():
    err = map_github_error(_resp(429, {"message": "too many requests"}, headers={"Retry-After": "30"}))
    assert isinstance(err, UpstreamRateLimitError)
    assert err.details == {"retry_after_seconds": 30}


def test_5xx_maps_to_upstream_unavailable():
    err = map_github_error(_resp(502, {"message": "bad gateway"}))
    assert isinstance(err, UpstreamUnavailableError)
    assert err.status == 503
