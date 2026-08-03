"""
providers.py — Protocol-based provider registry.

Providers are pluggable: Static, Callable, JsonFile, MCPTool, BrowserTool.
The host (Minis) injects credentials and transport — no keys live here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Protocol, runtime_checkable

from .models import Hit, SearchRequest


@runtime_checkable
class Provider(Protocol):
    """Any provider must implement `search()`."""

    name: str

    def search(self, request: SearchRequest) -> list[Hit]:
        ...


class StaticProvider:
    """Returns hard-coded results — useful for testing."""

    def __init__(self, name: str, hits: list[dict]):
        self.name = name
        self._hits = hits

    def search(self, request: SearchRequest) -> list[Hit]:
        return [Hit(provider=self.name, **h) for h in self._hits]


class CallableProvider:
    """Wraps a Python callable as a provider."""

    def __init__(self, name: str, fn: Callable[[SearchRequest], list[Hit]]):
        self.name = name
        self._fn = fn

    def search(self, request: SearchRequest) -> list[Hit]:
        return self._fn(request)


class JsonFileProvider:
    """Reads results from a JSON file on disk."""

    def __init__(self, name: str, path: str | Path):
        self.name = name
        self._path = Path(path)

    def search(self, request: SearchRequest) -> list[Hit]:
        data = json.loads(self._path.read_text())
        return [Hit(provider=self.name, **h) for h in data]


class MCPToolProvider:
    """Calls an MCP server tool — host injects the MCP client.

    The `mcp_call` callable is provided by the host environment.
    Signature: mcp_call(server: str, tool: str, arguments: dict) -> dict
    """

    def __init__(self, name: str, server: str, tool: str, mcp_call: Callable):
        self.name = name
        self._server = server
        self._tool = tool
        self._mcp_call = mcp_call

    def search(self, request: SearchRequest) -> list[Hit]:
        raw = self._mcp_call(self._server, self._tool, {"query": request.topic})
        items = raw.get("results", []) if isinstance(raw, dict) else []
        return [
            Hit(
                provider=self.name,
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                raw=item,
            )
            for item in items
        ]


class BrowserToolProvider:
    """Uses browser automation (browser_use) to scrape search results.

    The `browser_search` callable is provided by the host.
    Signature: browser_search(query: str) -> list[dict]
    """

    def __init__(self, name: str, browser_search: Callable[[str], list[dict]]):
        self.name = name
        self._browser_search = browser_search

    def search(self, request: SearchRequest) -> list[Hit]:
        raw_items = self._browser_search(request.topic)
        return [
            Hit(
                provider=self.name,
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                raw=item,
            )
            for item in raw_items
        ]


class ProviderRegistry:
    """Manages active providers — activate / deactivate dynamically."""

    def __init__(self):
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider):
        self._providers[provider.name] = provider

    def activate(self, name: str):
        """No-op if already registered — providers are always 'active' once registered."""
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not registered")

    def deactivate(self, name: str):
        self._providers.pop(name, None)

    def get(self, name: str) -> Provider:
        return self._providers[name]

    def all(self) -> list[Provider]:
        return list(self._providers.values())

    def search_all(self, request: SearchRequest) -> dict[str, list[Hit]]:
        """Fan-out: call all providers, collect results per provider."""
        return {p.name: p.search(request) for p in self._providers.values()}