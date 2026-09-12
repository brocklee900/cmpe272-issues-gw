from fastapi import Request

from app.config import Settings, get_settings
from app.github_client import GitHubClient


def get_settings_dep() -> Settings:
    return get_settings()


def get_github_client(request: Request) -> GitHubClient:
    """Reuses the single AsyncClient created at app startup (see main.py's
    lifespan) so we get connection pooling instead of a new client per request."""
    return GitHubClient(get_settings(), client=request.app.state.http_client)
