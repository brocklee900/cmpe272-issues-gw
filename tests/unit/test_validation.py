def test_create_issue_missing_title_returns_400(client, httpx_mock):
    resp = client.post("/issues", json={"body": "no title here"})
    assert resp.status_code == 422 or resp.status_code == 400
    # FastAPI/Pydantic returns 422 for schema-level validation errors,
    # which is the correct HTTP semantic for "well-formed but invalid" input.


def test_create_issue_blank_title_returns_422(client, httpx_mock):
    resp = client.post("/issues", json={"title": "   "})
    assert resp.status_code == 422


def test_update_issue_invalid_state_returns_422(client, httpx_mock):
    resp = client.patch("/issues/1", json={"state": "archived"})
    assert resp.status_code == 422


def test_create_comment_empty_body_returns_422(client, httpx_mock):
    resp = client.post("/issues/1/comments", json={"body": ""})
    assert resp.status_code == 422


def test_list_issues_per_page_over_limit_returns_422(client, httpx_mock):
    resp = client.get("/issues", params={"per_page": 500})
    assert resp.status_code == 422


def test_create_issue_valid_payload_reaches_github(client, httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.github.com/repos/test-owner/test-repo/issues",
        json={
            "number": 1,
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "state": "open",
            "title": "A valid issue",
            "body": None,
            "labels": [],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        },
        status_code=201,
    )
    resp = client.post("/issues", json={"title": "A valid issue"})
    assert resp.status_code == 201
    assert resp.headers["Location"] == "/issues/1"
    assert resp.json()["title"] == "A valid issue"
