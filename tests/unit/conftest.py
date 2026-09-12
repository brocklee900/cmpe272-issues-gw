import os
import tempfile
from pathlib import Path

import pytest

# Set required env vars before anything imports app.config, so Settings()
# doesn't blow up at import time in CI/local test runs.
os.environ.setdefault("GITHUB_TOKEN", "test-token")
os.environ.setdefault("GITHUB_OWNER", "test-owner")
os.environ.setdefault("GITHUB_REPO", "test-repo")
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("PORT", "8000")

from fastapi.testclient import TestClient  # noqa: E402

from app import store as store_module  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def tmp_event_store(monkeypatch):
    """Point the event store at a throwaway SQLite file per test so tests
    don't share dedupe state."""
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "events.db"
    fresh_store = store_module.EventStore(db_path=db_path)
    monkeypatch.setattr(store_module, "_default_store", fresh_store)
    return fresh_store


@pytest.fixture
def client(tmp_event_store):
    with TestClient(app) as c:
        yield c
