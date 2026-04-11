from __future__ import annotations

import unittest

from egloon_rule_hub.parsers.clash import parse_clash_rule_provider
from egloon_rule_hub.parsers.egern import parse_egern_rule_set
from egloon_rule_hub.parsers.loon import extract_loon_sections, parse_loon_list


class ParserTests(unittest.TestCase):
    def test_parse_loon_list(self) -> None:
        rules = parse_loon_list(
            "# comment\nDOMAIN,openai.com\nDOMAIN-SUFFIX,chatgpt.com\n"
        )
        self.assertEqual(
            [(rule.type, rule.value) for rule in rules],
            [("DOMAIN", "openai.com"), ("DOMAIN-SUFFIX", "chatgpt.com")],
        )

    def test_extract_loon_sections_preserves_headings(self) -> None:
        sections = extract_loon_sections(
            "# Apple Intelligence\n"
            "DOMAIN,apple-relay.apple.com\n"
            "# > Claude\n"
            "DOMAIN-SUFFIX,claude.ai\n"
            "DOMAIN-SUFFIX,anthropic.com\n"
        )
        self.assertEqual([section.heading for section in sections], ["Apple Intelligence", "> Claude"])
        self.assertEqual(
            [[rule.render() for rule in section.rules] for section in sections],
            [
                ["DOMAIN,apple-relay.apple.com"],
                ["DOMAIN-SUFFIX,claude.ai", "DOMAIN-SUFFIX,anthropic.com"],
            ],
        )

    def test_extract_loon_sections_supports_ungrouped_rules(self) -> None:
        sections = extract_loon_sections(
            "DOMAIN,openai.com\n"
            "# > Group\n"
            "DOMAIN-SUFFIX,chatgpt.com\n"
        )
        self.assertEqual([section.heading for section in sections], [None, "> Group"])
        self.assertEqual(
            [[rule.render() for rule in section.rules] for section in sections],
            [["DOMAIN,openai.com"], ["DOMAIN-SUFFIX,chatgpt.com"]],
        )

    def test_parse_clash_rule_provider(self) -> None:
        rules = parse_clash_rule_provider(
            "payload:\n  - DOMAIN,openai.com\n  - DOMAIN-SUFFIX,chatgpt.com\n"
        )
        self.assertEqual(
            [(rule.type, rule.value) for rule in rules],
            [("DOMAIN", "openai.com"), ("DOMAIN-SUFFIX", "chatgpt.com")],
        )

    def test_parse_egern_rule_set(self) -> None:
        rules = parse_egern_rule_set(
            "domain_set:\n  - openai.com\ndomain_suffix_set:\n  - chatgpt.com\n"
        )
        self.assertEqual(
            [(rule.type, rule.value) for rule in rules],
            [("DOMAIN", "openai.com"), ("DOMAIN-SUFFIX", "chatgpt.com")],
        )


if __name__ == "__main__":
    unittest.main()
