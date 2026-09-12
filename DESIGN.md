# Design Note

## Error mapping
GitHub's error responses (401/403/404/422/429/5xx) are translated in
`app/errors.py::map_github_error` into a small, closed set of `AppError`
subclasses, each carrying an HTTP status and a machine-readable `error`
code (`upstream_auth_error`, `not_found`, `rate_limited`, etc.). A single
FastAPI exception handler (`app_error_handler`) turns any `AppError` into
the shared `ErrorResponse` shape `{ error, message, status, details }`,
so every route — regardless of which GitHub call failed — returns a
consistent error body. The one ambiguous case is GitHub's `403`, which it
overloads for both "forbidden" and "secondary rate limit": we disambiguate
using the `X-RateLimit-Remaining` header rather than guessing from the
message text.

## Pagination strategy
We don't reimplement GitHub's pagination logic — we forward it. The
GitHub response's `Link` header (RFC 5988) is passed straight through on
`GET /issues` so clients can follow `rel="next"`/`rel="last"` exactly as
they would against GitHub directly. `app/pagination.py` additionally
parses that header into a dict and exposes convenience headers
(`X-Page-Next`, `X-Page-Last`, ...) for clients that don't want to parse
Link headers themselves. `page`/`per_page` query params are passed
through 1:1, with `per_page` capped at 100 to match GitHub's own limit,
enforced at the schema level (422 if violated) rather than silently
clamped, so clients get clear feedback.

## Webhook dedupe
GitHub redelivers webhooks it believes may have failed (timeout, 5xx,
etc.), so the same delivery can arrive more than once. We dedupe on
`delivery_id:action` (falling back to a synthetic key if a delivery ID is
ever missing, e.g. local testing) stored as the primary key in a small
SQLite table. A redelivered event is detected via a lookup, logged, and
acknowledged with the same 204 — without being reprocessed or re-stored —
so retries are safe and cheap. SQLite (rather than in-memory) was chosen
so dedupe state survives a restart, which matters if the service is
redeployed mid-burst of retries.

## Security trade-offs
- The webhook signature is verified against the **raw request bytes**
  before any JSON parsing happens, and compared with `hmac.compare_digest`
  (constant-time) rather than `==`, to avoid both signature-forgery and
  timing side-channels.
- `WEBHOOK_SECRET` and `GITHUB_TOKEN` are read from environment variables
  only; neither is ever logged, and error messages that include GitHub's
  response body are truncated to avoid accidentally leaking token
  fragments embedded in error text.
- The one trade-off: we trust `X-GitHub-Event`/`X-GitHub-Delivery` header
  values as-is once the signature passes, rather than re-deriving them
  from the payload — this is standard practice (GitHub signs the body,
  not the headers) but means a compromised secret would allow an attacker
  to also spoof event/delivery metadata, not just the payload.
- The GitHub PAT is a fine-grained token scoped to a single repo with only
  `Issues: Read and Write`, minimizing blast radius if it leaks.

## Operational lessons from live testing
Two non-obvious issues surfaced only when wiring this up against real
GitHub, rather than mocks, and are worth calling out since they're the
kind of thing that looks like an application bug but isn't:

- **Webhook Content-Type is a GitHub-side setting, not something we
  control.** GitHub's webhook config defaults to
  `application/x-www-form-urlencoded`, which wraps the JSON payload as a
  `payload=` form field rather than sending it as the request body.
  Because signature verification happens over the raw bytes before we
  attempt to parse JSON, a misconfigured webhook fails cleanly with a 400
  `invalid_payload` (not a 401), which was a useful signal in practice for
  telling "wrong secret" apart from "wrong content type" during setup.
- **Test isolation between unit and integration suites matters more than
  it looks.** Dummy credentials set via `os.environ.setdefault(...)` for
  the mocked unit tests are environment-wide, not test-file-scoped — if
  that setup code lives in a `conftest.py` visible to the integration
  tests too, it silently overrides real `.env` values (env vars take
  priority over `.env` file values), and integration tests fail against
  GitHub with a misleading 401 rather than an obviously-wrong error. This
  is why the dummy-credential setup lives in `tests/unit/conftest.py`
  specifically, not `tests/conftest.py`.

