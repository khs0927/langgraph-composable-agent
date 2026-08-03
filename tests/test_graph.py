import unittest
from composable_search.models import Hit
from composable_search.providers import ProviderRegistry, StaticProvider
from composable_search.normalization import canonical_url, deduplicate
from composable_search.graph import build_graph, run_search


class TestComposableSearch(unittest.TestCase):
    def setUp(self):
        self.registry = ProviderRegistry()
        self.registry.register(StaticProvider("test_a", [
            {"url": "http://example.com/a1?utm=test", "title": "Page 1", "snippet": "..."},
            {"url": "http://example.com/a2", "title": "Page 2", "snippet": "..."},
        ]))
        self.registry.register(StaticProvider("test_b", [
            {"url": "http://example.com/a1", "title": "Page 1 Dupe", "snippet": "..."},
            {"url": "http://example.com/b1", "title": "Page 3", "snippet": "..."},
        ]))

    def test_canonical(self):
        self.assertEqual(
            canonical_url("http://example.com/a1?utm=test"),
            "http://example.com/a1"
        )

    def test_deduplicate(self):
        hits = [
            Hit(url="http://example.com/a1?utm=test", provider="test_a", title="X", snippet="."),
            Hit(url="http://example.com/a1", provider="test_b", title="X", snippet="."),
        ]
        self.assertEqual(len(deduplicate(hits)), 1)

    def test_graph_run(self):
        report = run_search(self.registry, "unit-test-topic")
        self.assertTrue(report.verified)
        self.assertGreater(len(report.sources), 0)


if __name__ == "__main__":
    unittest.main()