from __future__ import annotations

import unittest

from egloon_rule_hub.emitters.clash import render_clash_rule_provider
from egloon_rule_hub.emitters.egern import render_egern_rule_set
from egloon_rule_hub.emitters.loon import render_loon_rules
from egloon_rule_hub.emitters.loon_lsr import render_loon_lsr
from egloon_rule_hub.model.rules import Rule


class EmitterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = [
            Rule("DOMAIN", "openai.com"),
            Rule("DOMAIN-SUFFIX", "chatgpt.com"),
        ]

    def test_render_loon_rules(self) -> None:
        rendered = render_loon_rules(self.rules)
        self.assertEqual(rendered, "DOMAIN,openai.com\nDOMAIN-SUFFIX,chatgpt.com\n")

    def test_render_loon_lsr_preserves_selected_source_headings(self) -> None:
        rendered = render_loon_lsr(
            service_name="OpenAI",
            rules=self.rules,
            source_texts=[
                "# Apple Intelligence\nDOMAIN,openai.com\n# > ChatGPT\nDOMAIN-SUFFIX,chatgpt.com\n"
            ],
        )
        self.assertEqual(
            rendered,
            "# Apple Intelligence\nDOMAIN,openai.com\n\n# > ChatGPT\nDOMAIN-SUFFIX,chatgpt.com\n",
        )

    def test_render_loon_lsr_falls_back_to_single_header(self) -> None:
        rendered = render_loon_lsr(
            service_name="OpenAI",
            rules=self.rules,
            source_texts=["DOMAIN,openai.com\nDOMAIN-SUFFIX,chatgpt.com\n"],
        )
        self.assertEqual(
            rendered,
            "# > OpenAI\nDOMAIN,openai.com\nDOMAIN-SUFFIX,chatgpt.com\n",
        )

    def test_render_clash_rule_provider(self) -> None:
        rendered = render_clash_rule_provider(self.rules)
        self.assertIn("payload:", rendered)
        self.assertIn("- DOMAIN,openai.com", rendered)

    def test_render_egern_rule_set(self) -> None:
        rendered = render_egern_rule_set(self.rules)
        self.assertIn("domain_set:", rendered)
        self.assertIn("domain_suffix_set:", rendered)

    def test_render_egern_strips_ip_rule_suffix_flags(self) -> None:
        rendered = render_egern_rule_set([Rule("IP-CIDR", "1.1.1.0/24,no-resolve")])
        self.assertIn("ip_cidr_set:", rendered)
        self.assertIn("- 1.1.1.0/24", rendered)
        self.assertNotIn("no-resolve", rendered)

    def test_render_egern_dedupes_after_ip_rule_normalization(self) -> None:
        rendered = render_egern_rule_set(
            [
                Rule("IP-CIDR", "1.1.1.0/24"),
                Rule("IP-CIDR", "1.1.1.0/24,no-resolve"),
            ]
        )
        self.assertEqual(rendered.count("1.1.1.0/24"), 1)


if __name__ == "__main__":
    unittest.main()
