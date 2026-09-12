import json

from app.webhook_verify import compute_signature, verify_signature

SECRET = "test-secret"


def test_valid_signature_is_accepted():
    body = json.dumps({"action": "opened"}).encode()
    sig = compute_signature(SECRET, body)
    assert verify_signature(SECRET, body, sig) is True


def test_invalid_signature_is_rejected():
    body = json.dumps({"action": "opened"}).encode()
    assert verify_signature(SECRET, body, "sha256=deadbeef") is False


def test_missing_signature_is_rejected():
    body = json.dumps({"action": "opened"}).encode()
    assert verify_signature(SECRET, body, None) is False


def test_tampered_body_is_rejected():
    body = json.dumps({"action": "opened"}).encode()
    sig = compute_signature(SECRET, body)
    tampered_body = json.dumps({"action": "closed"}).encode()
    assert verify_signature(SECRET, tampered_body, sig) is False


def test_wrong_secret_is_rejected():
    body = json.dumps({"action": "opened"}).encode()
    sig = compute_signature(SECRET, body)
    assert verify_signature("a-different-secret", body, sig) is False


def test_webhook_endpoint_rejects_bad_signature(client):
    resp = client.post(
        "/webhook",
        content=json.dumps({"action": "opened", "issue": {"number": 1}}),
        headers={
            "X-Hub-Signature-256": "sha256=not-the-real-signature",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401


def test_webhook_endpoint_accepts_valid_signature(client):
    payload = json.dumps({"action": "opened", "issue": {"number": 1}}).encode()
    sig = compute_signature(SECRET, payload)
    resp = client.post(
        "/webhook",
        content=payload,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 204


def test_webhook_endpoint_rejects_unknown_event(client):
    payload = json.dumps({"action": "opened"}).encode()
    sig = compute_signature(SECRET, payload)
    resp = client.post(
        "/webhook",
        content=payload,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "some_unsupported_event",
            "X-GitHub-Delivery": "delivery-2",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 400
