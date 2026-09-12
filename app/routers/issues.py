from typing import Optional

from fastapi import APIRouter, Depends, Query, Response, status

from app.dependencies import get_github_client
from app.github_client import GitHubClient
from app.pagination import parse_link_header
from app.schemas import CommentCreate, CommentOut, IssueCreate, IssueOut, IssueUpdate, ListState

router = APIRouter(prefix="/issues", tags=["issues"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=IssueOut)
async def create_issue(
    payload: IssueCreate,
    response: Response,
    client: GitHubClient = Depends(get_github_client),
):
    data = await client.create_issue(payload.title, payload.body, payload.labels)
    issue = IssueOut.from_github(data)
    response.headers["Location"] = f"/issues/{issue.number}"
    return issue


@router.get("", response_model=list[IssueOut])
async def list_issues(
    response: Response,
    state: ListState = Query(default="open"),
    labels: Optional[str] = Query(default=None, description="Comma-separated label names"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=100),
    client: GitHubClient = Depends(get_github_client),
):
    raw_issues, headers = await client.list_issues(state=state, labels=labels, page=page, per_page=per_page)
    # GitHub's issues endpoint also returns PRs; filter those out.
    filtered = [i for i in raw_issues if "pull_request" not in i]

    link_header = headers.get("link") or headers.get("Link")
    if link_header:
        response.headers["Link"] = link_header
    for rel, url in parse_link_header(link_header).items():
        response.headers[f"X-Page-{rel.capitalize()}"] = url

    return [IssueOut.from_github(i) for i in filtered]


@router.get("/{number}", response_model=IssueOut)
async def get_issue(number: int, client: GitHubClient = Depends(get_github_client)):
    data = await client.get_issue(number)
    return IssueOut.from_github(data)


@router.patch("/{number}", response_model=IssueOut)
async def update_issue(
    number: int,
    payload: IssueUpdate,
    client: GitHubClient = Depends(get_github_client),
):
    data = await client.update_issue(
        number, title=payload.title, body=payload.body, state=payload.state
    )
    return IssueOut.from_github(data)


@router.post("/{number}/comments", status_code=status.HTTP_201_CREATED, response_model=CommentOut)
async def create_comment(
    number: int,
    payload: CommentCreate,
    client: GitHubClient = Depends(get_github_client),
):
    data = await client.create_comment(number, payload.body)
    return CommentOut.from_github(data)
