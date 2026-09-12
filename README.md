# GitHub Issues Gateway

A small FastAPI service that wraps the GitHub REST API for Issues on a
single repository: issue CRUD + comments, a validated webhook receiver,
an OpenAPI 3.1 contract, and unit + integration tests.

## Contents
- [Setup](#setup)
- [Running locally](#running-locally-non-docker)
- [Running with Docker](#running-with-docker)
- [Environment variables](#environment-variables--scopes)
- [API examples](#api-examples)
- [Webhook setup](#webhook-setup)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Setup

**Requires Python 3.12** (not 3.13/3.14 — `pydantic-core` doesn't ship
prebuilt wheels for newer versions yet, so `pip install` will try to
compile it from Rust source and fail unless you have a full Rust
toolchain). If `python --version` shows something else, install 3.12
from python.org and use `py -3.12` to create the venv below.

1. Create a dedicated GitHub repo you control (private is fine) — this is
   the repo the service will manage issues in.
2. Create a **Fine-Grained Personal Access Token** scoped to that repo
   only, with **Issues: Read and Write** permission.
   (Settings → Developer settings → Fine-grained tokens → Generate new token)
3. Copy `.env.example` to `.env` and fill in your values:

   ```bash
   cp .env.example .env
   ```

## Running locally (non-Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The service is now at `http://localhost:8000`. Interactive docs (from
FastAPI's own schema) are at `http://localhost:8000/docs`; the
hand-written contract lives in `openapi.yaml`.

## Running with Docker

Requires **Docker Desktop** installed and its engine actually running (the
whale icon in your system tray should be static, not animating — if the
build fails with something like `failed to connect to the docker API at
npipe:...`, Docker Desktop isn't running yet; open it and wait for it to
finish starting).

```bash
docker build -t github-issues-gateway .
docker run --rm -it --env-file .env -p 8000:8000 github-issues-gateway
```

Or with `docker-compose`:

```bash
docker compose up --build
```

## Environment variables & scopes

| Variable         | Description                                        |
|-------------------|----------------------------------------------------|
| `GITHUB_TOKEN`    | Fine-grained PAT (or GitHub App token) — Issues: Read/Write only |
| `GITHUB_OWNER`    | Repo owner/org, e.g. `andrewbond`                   |
| `GITHUB_REPO`     | Repo name, e.g. `cmpe272-issues-gw`                 |
| `WEBHOOK_SECRET`  | Shared secret for verifying webhook HMAC signatures |
| `PORT`            | Port this service listens on                        |

## API examples

Create an issue:
```bash
curl -X POST http://localhost:8000/issues \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug: login fails", "body": "Steps to reproduce...", "labels": ["bug"]}'
```

List open issues:
```bash
curl "http://localhost:8000/issues?state=open&per_page=20"
```

Get a single issue:
```bash
curl http://localhost:8000/issues/42
```

Update (rename + close) an issue:
```bash
curl -X PATCH http://localhost:8000/issues/42 \
  -H "Content-Type: application/json" \
  -d '{"title": "Bug: login fails (fixed)", "state": "closed"}'
```

Add a comment:
```bash
curl -X POST http://localhost:8000/issues/42/comments \
  -H "Content-Type: application/json" \
  -d '{"body": "Fixed in #43."}'
```

View recent webhook deliveries (debugging):
```bash
curl http://localhost:8000/events
```

Health check:
```bash
curl http://localhost:8000/healthz
```

## Webhook setup

1. Run the service locally: `uvicorn app.main:app --reload --port 8000`.
2. Start a public tunnel, e.g.:
   ```bash
   ngrok http 8000
   ```
3. In your test repo: **Settings → Webhooks → Add webhook**
   - Payload URL: `https://<your-tunnel-domain>/webhook`
   - **Content type: `application/json`** — this dropdown defaults to
     `application/x-www-form-urlencoded`, which wraps the payload as
     `payload=<url-encoded-json>` instead of sending raw JSON. If you leave
     it on the default, every delivery will fail with a 400
     `invalid_payload` error even though the signature check passes. Make
     sure you explicitly switch it to `application/json`.
   - Secret: the same value as `WEBHOOK_SECRET` in your `.env`
   - Events: select **Issues** and **Issue comments**
4. GitHub will send a `ping` event immediately — check `GET /events` to
   confirm it was received and recorded.
5. Create or comment on an issue in the repo to trigger a real delivery.

**Redelivery:** From the webhook's "Recent Deliveries" tab in GitHub, you
can click any past delivery and hit **Redeliver**. The service dedupes on
`delivery_id + action`, so redelivering the same event is a safe no-op —
you'll get a `204` both times but it's only stored once (verify via
`GET /events`).

## Testing

Unit tests (fast, fully mocked, no network access needed):
```bash
pytest
# or: make test
```

`tests/unit/conftest.py` sets dummy credentials (`test-owner`, `test-token`,
etc.) so these tests never touch the network or your real `.env`.
`tests/integration/` has no such conftest, so those tests load your actual
`.env` and hit the real GitHub API — keep the two separate if you add more
tests, or credentials will bleed across suites in the wrong direction.

With coverage:
```bash
pytest --cov=app --cov-report=term-missing
```

Integration tests (hit the **real** GitHub API against your configured
test repo — costs real API calls and creates/closes real issues):
```bash
RUN_INTEGRATION_TESTS=1 pytest tests/integration -v
# or: make test-integration
```

The webhook integration test additionally requires a live server + tunnel
+ a real triggered delivery — see the docstring in
`tests/integration/test_webhook_integration.py` for the exact steps.

## Project layout

```
app/
  main.py            FastAPI app, lifespan, exception handlers
  config.py          Settings loaded from environment variables
  github_client.py   Async GitHub REST API wrapper
  schemas.py         Pydantic request/response models
  errors.py          AppError types + GitHub error mapping
  pagination.py      Link-header parsing
  webhook_verify.py  HMAC signature verification
  store.py           SQLite-backed webhook event store (dedupe)
  routers/           issues.py, webhook.py, events.py, health.py
tests/
  unit/              Fully mocked unit tests
  integration/        Tests against the real GitHub API (opt-in)
openapi.yaml         OpenAPI 3.1 contract
DESIGN.md            Design note: error mapping, pagination, dedupe, security
```

## Troubleshooting

**`pip install` fails building `pydantic-core` with a Rust/maturin/cargo
error mentioning PyO3.** You're on Python 3.13+/3.14. Install Python 3.12
specifically and recreate the venv with `py -3.12 -m venv .venv`.

**PowerShell's `curl` shows a "Security Warning: Script Execution Risk"
prompt, or `curl https://...` fails with an SSL/connection error.** On
Windows, `curl` is aliased to `Invoke-WebRequest`, which tries to parse
responses as HTML. Use `curl.exe` (the real curl, note the `.exe`) or
`Invoke-RestMethod` instead — and use `http://`, not `https://`, since
this service doesn't run TLS locally.

**`GET /events` (or anything touching the event store) returns a 500 with
`sqlite3.OperationalError: unable to open database file`.** The `data/`
directory the SQLite file lives in doesn't exist yet on a fresh checkout.
It's created automatically on first run in the current version of
`app/store.py` — if you're on an older copy, make sure `EventStore.__init__`
calls `self._db_path.parent.mkdir(parents=True, exist_ok=True)`
unconditionally, not only when a custom `db_path` is passed in.

**Every webhook delivery returns `400 {"error": "invalid_payload", ...}`
even though the signature check passes.** Your webhook's **Content type**
in GitHub's settings is set to `application/x-www-form-urlencoded` (the
default) instead of `application/json`. Fix it in Settings → Webhooks →
(your webhook) → Content type.

**Integration tests fail with 401 from GitHub, or log
`"Starting up, targeting repo test-owner/test-repo"` instead of your real
repo.** `tests/unit/conftest.py`'s dummy credentials are leaking into the
integration run. Confirm that conftest lives under `tests/unit/`, not
directly under `tests/` — if it's at the top level, its `os.environ`
overrides apply to every test in the tree, including integration tests
that need your real `.env`.

**`docker build` fails with `failed to connect to the docker API at
npipe:////./pipe/docker_engine`.** Docker Desktop isn't running. Open it
from the Start menu and wait for the tray icon to stop animating before
retrying.

**`docker build -t github-issues-gateway` (no trailing path) errors with
`'docker buildx build' requires 1 argument`.** Docker needs a build
context — add a `.` at the end: `docker build -t github-issues-gateway .`

