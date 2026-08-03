"""
models.py — Pydantic domain models for the composable search agent.

Typed contracts that flow through the LangGraph StateGraph:
  SearchRequest → Hit[] → NormalizedHit[] → Evidence → AgentReport
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class SearchRequest(BaseModel):
    """User's original request, decomposed into a typed query."""

    topic: str = Field(..., description="The search topic / question")
    max_results_per_provider: int = Field(5, ge=1, le=20)
    min_sources: int = Field(2, ge=1, description="Minimum independent sources required")
    recency_days: Optional[int] = Field(
        None, ge=1, description="If set, reject results older than this many days"
    )


class Hit(BaseModel):
    """Raw result from a single provider — pre-normalization."""

    provider: str
    title: str
    url: str
    snippet: str = ""
    published: Optional[datetime] = None
    raw: dict = Field(default_factory=dict, description="Provider-specific payload")


class NormalizedHit(BaseModel):
    """Deduplicated, canonical-URL result ready for evidence review."""

    provider: str
    title: str
    url: str  # canonical
    snippet: str = ""
    published: Optional[datetime] = None
    content_hash: str = Field(..., description="SHA-256 of title+url for dedup")
    source_domain: str = ""

    class Config:
        frozen = True  # hashable for set-based dedup


class Evidence(BaseModel):
    """Evaluated evidence package — scored before final review."""

    hits: list[NormalizedHit]
    independent_sources: int
    has_recency: bool
    citation_accuracy: float = Field(..., ge=0.0, le=1.0)
    redundancy_removed: int
    non_trivial: bool
    score: float = Field(..., ge=0.0, le=1.0)
    passed: bool

    # Weights for score calculation
    W_SOURCE = 0.30
    W_RECENCY = 0.20
    W_CITATION = 0.25
    W_REDUNDANCY = 0.15
    W_TRIVIAL = 0.10
    PASS_THRESHOLD = 0.82


class AgentReport(BaseModel):
    """The final synthesized output sent back to the user."""

    topic: str
    summary: str
    sources: list[NormalizedHit]
    evidence: Evidence
    verified: bool = False
    reviewer_notes: str = ""
    conflicts: list[str] = Field(default_factory=list)