from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

IssueState = Literal["open", "closed"]
ListState = Literal["open", "closed", "all"]


class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    body: Optional[str] = None
    labels: Optional[list[str]] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v


class IssueUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    body: Optional[str] = None
    state: Optional[IssueState] = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must not be blank")
        return v


class IssueOut(BaseModel):
    number: int
    html_url: str
    state: str
    title: str
    body: Optional[str] = None
    labels: list[str] = []
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_github(cls, data: dict) -> "IssueOut":
        return cls(
            number=data["number"],
            html_url=data["html_url"],
            state=data["state"],
            title=data["title"],
            body=data.get("body"),
            labels=[
                lbl["name"] if isinstance(lbl, dict) else lbl
                for lbl in data.get("labels", [])
            ],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1)


class CommentOut(BaseModel):
    id: int
    body: str
    user: str
    created_at: datetime
    html_url: str

    @classmethod
    def from_github(cls, data: dict) -> "CommentOut":
        return cls(
            id=data["id"],
            body=data.get("body") or "",
            user=data.get("user", {}).get("login", "unknown"),
            created_at=data["created_at"],
            html_url=data["html_url"],
        )


class ErrorResponse(BaseModel):
    error: str
    message: str
    status: int
    details: Optional[dict] = None


class WebhookEventOut(BaseModel):
    id: str
    event: str
    action: Optional[str] = None
    issue_number: Optional[int] = None
    timestamp: datetime
