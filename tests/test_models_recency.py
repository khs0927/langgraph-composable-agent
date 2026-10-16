import unittest
from datetime import datetime, timedelta, timezone

from composable_search.graph import _recency, run_search
from composable_search.models import Evidence, NormalizedHit
from composable_search.providers import ProviderRegistry, StaticProvider


def _hit(days_ago):
    pub = None if days_ago is None else datetime.now(timezone.utc) - timedelta(days=days_ago)
    return NormalizedHit(provider="p", title="t", url=f"http://x.com/{days_ago}",
                         content_hash=str(days_ago), published=pub)


class TestEvidenceModel(unittest.TestCase):
    def test_weights_are_classvars(self):
        self.assertNotIn("W_SOURCE", Evidence.model_fields)
        total = (Evidence.W_SOURCE + Evidence.W_RECENCY + Evidence.W_CITATION
                 + Evidence.W_REDUNDANCY + Evidence.W_TRIVIAL)
        self.assertAlmostEqual(total, 1.0)

    def test_normalized_hit_frozen_hashable(self):
        h = _hit(1)
        self.assertEqual(len({h, h}), 1)
        with self.assertRaises(Exception):
            h.title = "changed"


class TestRecency(unittest.TestCase):
    def test_not_requested(self):
        self.assertEqual(_recency([], None), (1.0, True))

    def test_window(self):
        score, ok = _recency([_hit(1), _hit(30), _hit(None), _hit(2)], 7)
        self.assertAlmostEqual(score, 0.5)
        self.assertTrue(ok)

    def test_all_stale(self):
        self.assertEqual(_recency([_hit(100)], 7), (0.0, False))

    def test_naive_datetime(self):
        h = NormalizedHit(provider="p", title="t", url="http://x.com", content_hash="h",
                          published=datetime.utcnow())
        self.assertEqual(_recency([h], 1), (1.0, True))

    def test_graph_rejects_undated_when_recency_required(self):
        reg = ProviderRegistry()
        reg.register(StaticProvider("a", [{"url": "http://a.com/1", "title": "A"}]))
        reg.register(StaticProvider("b", [{"url": "http://b.com/1", "title": "B"}]))
        report = run_search(reg, "topic", recency_days=7)
        self.assertFalse(report.evidence.has_recency)
        self.assertFalse(report.verified)


class TestCanonicalUrl(unittest.TestCase):
    def test_keeps_non_tracking_params(self):
        from composable_search.normalization import canonical_url
        self.assertEqual(
            canonical_url("HTTPS://Example.com:443/p?id=3&utm_source=x&gclid=y#frag"),
            "https://example.com/p?id=3",
        )


if __name__ == "__main__":
    unittest.main()
