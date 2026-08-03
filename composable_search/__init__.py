"""
composable_search — A composable, evidence-gated search agent framework.

Public API:
    from composable_search import (
        SearchRequest, Hit, NormalizedHit, Evidence, AgentReport,
        ProviderRegistry, StaticProvider, CallableProvider,
        JsonFileProvider, MCPToolProvider, BrowserToolProvider,
        canonical_url, deduplicate,
        build_graph, run_search,
        HermesAdapter,
        build_mission_graph,
    )
"""

from .models import (
    SearchRequest,
    Hit,
    NormalizedHit,
    Evidence,
    AgentReport,
)
from .providers import (
    ProviderRegistry,
    StaticProvider,
    CallableProvider,
    JsonFileProvider,
    MCPToolProvider,
    BrowserToolProvider,
)
from .normalization import canonical_url, deduplicate
from .graph import build_graph, run_search
from .hermes import HermesAdapter
from .agents import build_mission_graph

__version__ = "0.1.0"

__all__ = [
    "SearchRequest",
    "Hit",
    "NormalizedHit",
    "Evidence",
    "AgentReport",
    "ProviderRegistry",
    "StaticProvider",
    "CallableProvider",
    "JsonFileProvider",
    "MCPToolProvider",
    "BrowserToolProvider",
    "canonical_url",
    "deduplicate",
    "build_graph",
    "run_search",
    "HermesAdapter",
    "build_mission_graph",
]