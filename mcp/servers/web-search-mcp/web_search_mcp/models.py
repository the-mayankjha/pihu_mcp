from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str = ""
    rank: int
    provider: str
    published_at: datetime | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    provider: str
    took_ms: int
    cached: bool = False


class PageMetadata(BaseModel):
    title: str = ""
    description: str = ""
    author: str | None = None
    published_at: str | None = None
    canonical_url: str | None = None


class PageContent(BaseModel):
    url: str
    final_url: str
    status_code: int
    content_type: str
    title: str
    text: str
    metadata: PageMetadata
    truncated: bool = False
    took_ms: int


class Evidence(BaseModel):
    title: str
    url: str
    domain: str
    snippet: str = ""
    content: str = ""
    rank: int
    provider: str


class ResearchResponse(BaseModel):
    query: str
    sources: list[Evidence]
    took_ms: int
