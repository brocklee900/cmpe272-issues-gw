from fastapi import APIRouter, Query

from app.store import get_event_store

router = APIRouter(tags=["events"])


@router.get("/events")
async def list_events(limit: int = Query(default=50, ge=1, le=200)):
    store = get_event_store()
    return store.recent(limit=limit)
