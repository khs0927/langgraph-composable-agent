"""
graph.py — LangGraph StateGraph orchestrator.

Fan-out → parallel fetch → fan-in → evidence gate workflow.
"""
from __future__ import annotations

import operator
from datetime import datetime, timedelta, timezone
from typing import Annotated, TypedDict
from typing_extensions import Required

from langgraph.graph import StateGraph, START, END

from .models import SearchRequest, Hit, NormalizedHit, Evidence, AgentReport
from .providers import ProviderRegistry
from .normalization import deduplicate


class AgentState(TypedDict):
    """State managed by LangGraph with Annotated reducer for parallel results."""

    request: Required[SearchRequest]
    raw_hits: Annotated[list[Hit], operator.add]
    normalized_hits: list[NormalizedHit]
    evidence: Evidence
    report: AgentReport


def _recency(hits: list[NormalizedHit], recency_days: int | None) -> tuple[float, bool]:
    """Score how many hits fall inside the requested recency window.

    With no ``recency_days`` the criterion is not requested, so it is fully
    satisfied. Otherwise the score is the fraction of hits published within the
    window; undated hits count as not recent.
    """
    if recency_days is None:
        return 1.0, True
    if not hits:
        return 0.0, False
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=recency_days)
    recent = 0
    for h in hits:
        if h.published is None:
            continue
        pub = h.published if h.published.tzinfo else h.published.replace(tzinfo=timezone.utc)
        if pub >= cutoff:
            recent += 1
    return recent / len(hits), recent > 0


def build_graph(registry: ProviderRegistry) -> StateGraph:
    """Compile a StateGraph that fans out to all providers in parallel."""
    builder = StateGraph(AgentState)

    # ── Nodes ───────────────────────────────────────────────
    def planner_node(state: AgentState) -> dict:
        return {"raw_hits": []}

    def make_fetch_node(provider_name: str):
        def _node(state: AgentState) -> dict:
            provider = registry.get(provider_name)
            try:
                hits = provider.search(state["request"])
                return {"raw_hits": hits}
            except Exception:
                return {"raw_hits": []}
        return _node

    def normalize_node(state: AgentState) -> dict:
        normalized = deduplicate(state["raw_hits"])
        return {"normalized_hits": normalized}

    def evidence_gate_node(state: AgentState) -> dict:
        hits = state["normalized_hits"]
        req = state["request"]

        domains = {h.source_domain for h in hits if h.source_domain}
        independent_sources = len(domains)
        source_score = min(independent_sources / max(req.min_sources, 1), 1.0)

        recency_score, has_recency = _recency(hits, req.recency_days)

        citation_score = 1.0 if len(hits) > 0 else 0.0

        raw_count = len(state["raw_hits"])
        norm_count = len(hits)
        redundancy_removed = raw_count - norm_count
        redundancy_score = norm_count / max(raw_count, 1)

        non_trivial = norm_count > 0
        trivial_score = 1.0 if non_trivial else 0.0

        score = (
            source_score * Evidence.W_SOURCE
            + recency_score * Evidence.W_RECENCY
            + citation_score * Evidence.W_CITATION
            + redundancy_score * Evidence.W_REDUNDANCY
            + trivial_score * Evidence.W_TRIVIAL
        )
        passed = score >= Evidence.PASS_THRESHOLD

        evidence = Evidence(
            hits=hits,
            independent_sources=independent_sources,
            has_recency=has_recency,
            citation_accuracy=citation_score,
            redundancy_removed=redundancy_removed,
            non_trivial=non_trivial,
            score=round(score, 3),
            passed=passed,
        )
        return {"evidence": evidence}

    def reviewer_node(state: AgentState) -> dict:
        evidence = state["evidence"]
        req = state["request"]

        if not evidence.passed:
            summary = f"Warning: evidence score ({evidence.score}) below threshold ({Evidence.PASS_THRESHOLD})."
            verified = False
        else:
            summary = f"Search complete: {len(evidence.hits)} unique hits from {evidence.independent_sources} independent domains."
            verified = True

        report = AgentReport(
            topic=req.topic,
            summary=summary,
            sources=evidence.hits,
            evidence=evidence,
            verified=verified,
            reviewer_notes="Auto-verified by LangGraph Composable Agent.",
        )
        return {"report": report}

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("normalize", normalize_node)
    builder.add_node("evidence_gate", evidence_gate_node)
    builder.add_node("reviewer", reviewer_node)

    provider_names = [p.name for p in registry.all()]
    for name in provider_names:
        builder.add_node(f"fetch_{name}", make_fetch_node(name))

    # Edges
    builder.add_edge(START, "planner")
    for name in provider_names:
        builder.add_edge("planner", f"fetch_{name}")
        builder.add_edge(f"fetch_{name}", "normalize")
    builder.add_edge("normalize", "evidence_gate")
    builder.add_edge("evidence_gate", "reviewer")
    builder.add_edge("reviewer", END)

    return builder


def run_search(
    registry: ProviderRegistry, topic: str, recency_days: int | None = None
) -> AgentReport:
    """Compile and run the search graph in one call."""
    graph = build_graph(registry).compile()
    req = SearchRequest(topic=topic, recency_days=recency_days)
    final_state = graph.invoke({"request": req, "raw_hits": []})
    return final_state["report"]