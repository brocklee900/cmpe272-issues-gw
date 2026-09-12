import json

from app.webhook_verify import compute_signature

SECRET = "test-secret"


def _send(client, delivery_id="delivery-42"):
    payload = json.dumps({"action": "opened", "issue": {"number": 7}}).encode()
    sig = compute_signature(SECRET, payload)
    return client.post(
        "/webhook",
        content=payload,
        headers={
            "X-Hub-Signature-256": sig,
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        },
    )


def test_redelivered_event_is_idempotent(client):
    first = _send(client, "delivery-42")
    second = _send(client, "delivery-42")  # GitHub retries with the same delivery id
    assert first.status_code == 204
    assert second.status_code == 204

    events = client.get("/events").json()
    matching = [e for e in events if e["id"].startswith("delivery-42")]
    assert len(matching) == 1  # stored once, not twice


def test_events_endpoint_reflects_processed_deliveries(client):
    _send(client, "delivery-99")
    events = client.get("/events").json()
    assert any(e["issue_number"] == 7 for e in events)
