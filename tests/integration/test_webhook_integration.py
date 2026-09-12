"""
Manual/semi-automated webhook delivery test.

Automating this end-to-end (real GitHub -> public tunnel -> your running
server) isn't practical inside a plain pytest run, so this test is a
guided, skip-by-default check: it polls YOUR running server's /events
endpoint and asserts a real delivery showed up.

How to actually exercise this:
  1. Start your server:            uvicorn app.main:app --reload
  2. Start a tunnel:               ngrok http $PORT   (or cloudflared/smee)
  3. Configure the repo webhook to POST to <tunnel-url>/webhook with the
     same WEBHOOK_SECRET, subscribed to "Issues" and "Issue comments".
  4. Create or comment on an issue in the test repo.
  5. Run:  RUN_INTEGRATION_TESTS=1 WEBHOOK_INTEGRATION_BASE_URL=http://localhost:8000 \
           pytest tests/integration/test_webhook_integration.py -v
"""
import os
import time

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 and trigger a real delivery first (see module docstring)",
)


def test_a_real_delivery_was_recorded():
    base_url = os.environ.get("WEBHOOK_INTEGRATION_BASE_URL", "http://localhost:8000")
    deadline = time.time() + 30
    events = []
    while time.time() < deadline:
        resp = httpx.get(f"{base_url}/events", timeout=5)
        resp.raise_for_status()
        events = resp.json()
        if events:
            break
        time.sleep(2)

    assert events, (
        "No webhook deliveries found in /events. Make sure your tunnel and "
        "webhook are configured, and that you triggered a real event."
    )
    assert events[0]["event"] in {"issues", "issue_comment", "ping"}
