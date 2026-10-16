"""
normalization.py — Deduplication and canonical URL resolution.

Filters tracking parameters, generates content hashes, and deduplicates.
"""
from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .models import Hit, NormalizedHit

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                   "ref", "source", "fbclid", "gclid", "dclid"}


def canonical_url(url: str) -> str:
    """Remove tracking parameters and fragments, normalize scheme and domain."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]
        query = urlencode([
            (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm")
        ])
        # Drop tracking params and fragment
        return urlunparse((scheme, netloc, parsed.path, parsed.params, query, ""))
    except Exception:
        return url


def deduplicate(hits: list[Hit]) -> list[NormalizedHit]:
    """Deduplicate hits by canonical URL + title hash to produce unique NormalizedHit list."""
    seen: set[str] = set()
    normalized: list[NormalizedHit] = []

    for h in hits:
        cleaned = canonical_url(h.url)
        if not cleaned:
            continue

        content_bytes = cleaned.encode("utf-8")
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        if content_hash in seen:
            continue
        seen.add(content_hash)

        try:
            domain = urlparse(cleaned).netloc
            if domain.startswith("www."):
                domain = domain[4:]
        except Exception:
            domain = ""

        normalized.append(NormalizedHit(
            provider=h.provider,
            url=cleaned,
            content_hash=content_hash,
            source_domain=domain,
            title=h.title,
            published=h.published,
            snippet=h.snippet,
        ))

    return normalized