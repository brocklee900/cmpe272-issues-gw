"""
Thin async wrapper around the GitHub REST API for Issues, scoped to a
single configured repo. Centralizes auth headers, the required Accept
header, and error mapping so routers stay simple.
"""
from typing import Optional

import httpx

from app.config import Settings
from app.errors import map_github_error


class GitHubClient:
    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None):
        self._settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=settings.github_api_base,
            timeout=settings.request_timeout_seconds,
        )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._settings.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def aclose(self):
        if self._owns_client:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        resp = await self._client.request(method, path, headers=self._headers(), **kwargs)
        if resp.status_code >= 400:
            raise map_github_error(resp)
        return resp

    # --- Issues -----------------------------------------------------
    async def create_issue(self, title: str, body: Optional[str], labels: Optional[list[str]]) -> dict:
        payload: dict = {"title": title}
        if body is not None:
            payload["body"] = body
        if labels:
            payload["labels"] = labels
        resp = await self._request(
            "POST", f"/repos/{self._settings.repo_path}/issues", json=payload
        )
        return resp.json()

    async def list_issues(
        self,
        state: str = "open",
        labels: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> tuple[list[dict], dict]:
        params = {"state": state, "page": page, "per_page": per_page}
        if labels:
            params["labels"] = labels
        resp = await self._request(
            "GET", f"/repos/{self._settings.repo_path}/issues", params=params
        )
        return resp.json(), dict(resp.headers)

    async def get_issue(self, number: int) -> dict:
        resp = await self._request(
            "GET", f"/repos/{self._settings.repo_path}/issues/{number}"
        )
        return resp.json()

    async def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
    ) -> dict:
        payload = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        resp = await self._request(
            "PATCH", f"/repos/{self._settings.repo_path}/issues/{number}", json=payload
        )
        return resp.json()

    # --- Comments -----------------------------------------------------
    async def create_comment(self, number: int, body: str) -> dict:
        resp = await self._request(
            "POST",
            f"/repos/{self._settings.repo_path}/issues/{number}/comments",
            json={"body": body},
        )
        return resp.json()
