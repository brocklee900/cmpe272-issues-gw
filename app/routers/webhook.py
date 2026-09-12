import json
import logging

from fastapi import APIRouter, Header, Request, Response, status

from app.config import get_settings
from app.errors import AppError
from app.store import EventStore, get_event_store
from app.webhook_verify import verify_signature

logger = logging.getLogger("webhook")

router = APIRouter(tags=["webhook"])

KNOWN_EVENTS = {"ping", "issues", "issue_comment"}


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def receive_webhook(
    request: Request,
    response: Response,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
):
    settings = get_settings()
    raw_body = await request.body()

    # 1) Verify signature over the *raw* bytes before doing anything else.
    if not verify_signature(settings.webhook_secret, raw_body, x_hub_signature_256):
        raise AppError(401, "invalid_signature", "Webhook signature verification failed")

    # 2) Only now parse and validate the event type.
    if x_github_event not in KNOWN_EVENTS:
        raise AppError(400, "unknown_event", f"Unsupported event type: {x_github_event}")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise AppError(400, "invalid_payload", "Webhook body is not valid JSON")

    action = payload.get("action")
    issue_number = (payload.get("issue") or {}).get("number")

    # 3) Dedupe on delivery id + action so redeliveries are a no-op.
    if x_github_delivery:
        dedupe_key = f"{x_github_delivery}:{action}"
    else:
        dedupe_key = f"no-delivery-id:{x_github_event}:{action}:{issue_number}"

    store: EventStore = get_event_store()
    if store.already_processed(dedupe_key):
        logger.info("Duplicate delivery %s ignored", x_github_delivery)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    store.record(
        dedupe_key=dedupe_key,
        delivery_id=x_github_delivery,
        event=x_github_event,
        action=action,
        issue_number=issue_number,
        payload=payload,
    )

    logger.info(
        "Processed webhook event=%s action=%s issue=%s delivery=%s",
        x_github_event,
        action,
        issue_number,
        x_github_delivery,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
