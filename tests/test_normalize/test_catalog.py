from __future__ import annotations

import unittest
from pathlib import Path

from egloon_rule_hub.docs.render import write_markdown_docs
from egloon_rule_hub.model.catalog import load_catalog
from egloon_rule_hub.normalize.dedupe import dedupe_rules
from egloon_rule_hub.normalize.merge import merge_rule_streams
from egloon_rule_hub.model.rules import Rule


class CatalogTests(unittest.TestCase):
    def test_load_catalog(self) -> None:
        root = Path(__file__).resolve().parents[2]
        catalog = load_catalog(root)
        self.assertIn("OpenAI", catalog.services)
        self.assertIn("ai", catalog.bundles)
        self.assertIn("egern", catalog.targets)
        self.assertIn("blackmatrix7", catalog.sources)

    def test_dedupe_rules(self) -> None:
        rules = [
            Rule("DOMAIN", "openai.com"),
            Rule("DOMAIN", "openai.com"),
            Rule("DOMAIN-SUFFIX", "chatgpt.com"),
        ]
        deduped = dedupe_rules(rules)
        self.assertEqual(len(deduped), 2)

    def test_merge_rule_streams(self) -> None:
        merged = merge_rule_streams(
            [
                [Rule("DOMAIN", "openai.com")],
                [Rule("DOMAIN", "openai.com"), Rule("DOMAIN-SUFFIX", "chatgpt.com")],
            ]
        )
        self.assertEqual(
            [(rule.type, rule.value) for rule in merged],
            [("DOMAIN", "openai.com"), ("DOMAIN-SUFFIX", "chatgpt.com")],
        )

    def test_write_markdown_docs_includes_attribution_doc(self) -> None:
        root = Path(__file__).resolve().parents[2]
        catalog = load_catalog(root)
        write_markdown_docs(root, catalog)
        attribution = (root / "docs" / "attribution.md").read_text(encoding="utf-8")
        self.assertIn("# Attribution", attribution)
        self.assertIn("blackmatrix7", attribution)
        self.assertIn("ACL4SSR", attribution)


if __name__ == "__main__":
    unittest.main()
