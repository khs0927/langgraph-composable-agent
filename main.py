"""
main.py — CLI entry point for the Composable Search Agent framework.

Usage:
    python3 main.py --topic "quantum computing"
    python3 main.py --topic "AI safety" --mock
"""
from __future__ import annotations

import argparse
import json
import sys

from composable_search import (
    ProviderRegistry,
    StaticProvider,
    run_search,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Composable Search Agent CLI")
    parser.add_argument("--topic", default="LangGraph 1.2 features", help="Search topic")
    parser.add_argument("--mock", action="store_true", default=True, help="Use mock providers")
    args = parser.parse_args()

    print(f"🔍 [Composable Search Agent] Topic: '{args.topic}'")

    # Set up registry with mock providers
    registry = ProviderRegistry()
    
    registry.register(
        StaticProvider(
            "mock_arxiv",
            [
                {
                    "title": f"Recent Advances in {args.topic}",
                    "url": f"https://arxiv.org/abs/2608.01001?utm_source=twitter",
                    "snippet": f"This paper explores novel paradigms in {args.topic}.",
                },
                {
                    "title": f"Survey of {args.topic} Architectures",
                    "url": f"https://arxiv.org/abs/2608.01002",
                    "snippet": f"Comprehensive survey covering {args.topic}.",
                },
            ],
        )
    )

    registry.register(
        StaticProvider(
            "mock_news",
            [
                {
                    "title": f"{args.topic} Breakthrough Announced",
                    "url": f"https://news.example.com/tech/{args.topic.lower().replace(' ', '-')}",
                    "snippet": f"Industry leaders announced major milestones in {args.topic} today.",
                },
            ],
        )
    )

    try:
        report = run_search(registry, args.topic)
        print("\n" + "=" * 60)
        print(f"📊 REPORT SUMMARY:")
        print(f"  • Topic: {report.topic}")
        print(f"  • Status: {'✅ Verified' if report.verified else '❌ Failed Gate'}")
        print(f"  • Evidence Score: {report.evidence.score} (threshold {report.evidence.PASS_THRESHOLD})")
        print(f"  • Independent Sources: {report.evidence.independent_sources}")
        print(f"  • Unique Hits: {len(report.sources)}")
        print(f"\n📝 Summary:\n{report.summary}")
        print("=" * 60)
        return 0 if report.verified else 1
    except Exception as e:
        print(f"❌ Error during search run: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())