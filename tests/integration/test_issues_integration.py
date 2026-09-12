"""
These tests hit the REAL GitHub API against the repo configured in your
environment variables. They are skipped automatically unless
RUN_INTEGRATION_TESTS=1 is set, so `pytest` (unit tests only) stays fast
and safe to run anywhere, including CI without secrets.

Run explicitly with:
    RUN_INTEGRATION_TESTS=1 pytest tests/integration -v
"""
import os

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION_TESTS") != "1",
    reason="Set RUN_INTEGRATION_TESTS=1 and real GitHub env vars to run against a live repo",
)


@pytest.fixture
def live_client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_create_then_get_issue(live_client):
    create_resp = live_client.post(
        "/issues", json={"title": "[integration-test] created issue", "body": "created by pytest"}
    )
    assert create_resp.status_code == 201
    number = create_resp.json()["number"]

    get_resp = live_client.get(f"/issues/{number}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "[integration-test] created issue"

    # cleanup: close it so the test repo doesn't accumulate open issues
    live_client.patch(f"/issues/{number}", json={"state": "closed"})


def test_update_title_body_close_and_reopen(live_client):
    create_resp = live_client.post("/issues", json={"title": "[integration-test] update flow"})
    number = create_resp.json()["number"]

    patch_resp = live_client.patch(
        f"/issues/{number}", json={"title": "[integration-test] renamed", "body": "updated body"}
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == "[integration-test] renamed"

    close_resp = live_client.patch(f"/issues/{number}", json={"state": "closed"})
    assert close_resp.json()["state"] == "closed"

    reopen_resp = live_client.patch(f"/issues/{number}", json={"state": "open"})
    assert reopen_resp.json()["state"] == "open"

    live_client.patch(f"/issues/{number}", json={"state": "closed"})  # cleanup


def test_create_comment_and_list(live_client):
    create_resp = live_client.post("/issues", json={"title": "[integration-test] comment flow"})
    number = create_resp.json()["number"]

    comment_resp = live_client.post(f"/issues/{number}/comments", json={"body": "hello from pytest"})
    assert comment_resp.status_code == 201
    assert comment_resp.json()["body"] == "hello from pytest"

    live_client.patch(f"/issues/{number}", json={"state": "closed"})  # cleanup
