SAMPLE_ISSUE = {
    "number": 5,
    "html_url": "https://github.com/test-owner/test-repo/issues/5",
    "state": "open",
    "title": "Sample",
    "body": "body text",
    "labels": [{"name": "bug"}],
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


def test_get_issue_success(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/test-owner/test-repo/issues/5",
        json=SAMPLE_ISSUE,
        status_code=200,
    )
    resp = client.get("/issues/5")
    assert resp.status_code == 200
    assert resp.json()["labels"] == ["bug"]


def test_get_issue_not_found(client, httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/test-owner/test-repo/issues/999",
        json={"message": "Not Found"},
        status_code=404,
    )
    resp = client.get("/issues/999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_list_issues_filters_pull_requests_and_forwards_link_header(client, httpx_mock):
    pr_item = dict(SAMPLE_ISSUE, number=6, pull_request={"url": "..."})
    httpx_mock.add_response(
        method="GET",
        url="https://api.github.com/repos/test-owner/test-repo/issues?state=open&page=1&per_page=30",
        json=[SAMPLE_ISSUE, pr_item],
        status_code=200,
        headers={"Link": '<https://api.github.com/repos/o/r/issues?page=2>; rel="next"'},
    )
    resp = client.get("/issues")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1  # PR filtered out
    assert resp.headers["Link"].startswith("<https://api.github.com")
    assert resp.headers["X-Page-Next"] == "https://api.github.com/repos/o/r/issues?page=2"


def test_update_issue_close(client, httpx_mock):
    closed = dict(SAMPLE_ISSUE, state="closed")
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.github.com/repos/test-owner/test-repo/issues/5",
        json=closed,
        status_code=200,
    )
    resp = client.patch("/issues/5", json={"state": "closed"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "closed"


def test_update_issue_not_found(client, httpx_mock):
    httpx_mock.add_response(
        method="PATCH",
        url="https://api.github.com/repos/test-owner/test-repo/issues/999",
        json={"message": "Not Found"},
        status_code=404,
    )
    resp = client.patch("/issues/999", json={"state": "closed"})
    assert resp.status_code == 404


def test_create_comment_success(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/repos/test-owner/test-repo/issues/5/comments",
        json={
            "id": 100,
            "body": "a comment",
            "user": {"login": "octocat"},
            "created_at": "2026-01-01T00:00:00Z",
            "html_url": "https://github.com/test-owner/test-repo/issues/5#issuecomment-100",
        },
        status_code=201,
    )
    resp = client.post("/issues/5/comments", json={"body": "a comment"})
    assert resp.status_code == 201
    assert resp.json()["user"] == "octocat"


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
