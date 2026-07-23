from __future__ import annotations

import unittest
from pathlib import Path

from egloon_rule_hub.build import (
    _supplements_for_variant,
    build_service_supplements,
    build_target_artifact,
)
from egloon_rule_hub.model.catalog import load_catalog
from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.normalize.supplement import append_missing_rules
from egloon_rule_hub.parsers.v2fly import parse_v2fly_domain_list


class SupplementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.catalog = load_catalog(self.repo_root)

    def test_parses_v2fly_rules_attributes_and_includes(self) -> None:
        parsed = parse_v2fly_domain_list(
            """
            example.com
            full:api.example.com @ads
            regexp:^edge-[0-9]+\\.example\\.net$
            include:example-extra
            """
        )

        self.assertEqual(
            parsed.rules,
            [
                Rule("DOMAIN-SUFFIX", "example.com"),
                Rule("DOMAIN", "api.example.com"),
                Rule(
                    "DOMAIN-REGEX",
                    r"^edge-[0-9]+\.example\.net$",
                ),
            ],
        )
        self.assertEqual(parsed.includes, ["example-extra"])

    def test_only_appends_semantically_missing_rules(self) -> None:
        primary = [
            Rule("DOMAIN-SUFFIX", "example.com"),
            Rule("IP-CIDR", "192.0.2.0/24"),
        ]
        supplement = [
            Rule("DOMAIN", "api.example.com"),
            Rule("DOMAIN-SUFFIX", "new.example"),
            Rule("IP-CIDR", "192.0.2.10/32"),
        ]

        self.assertEqual(
            append_missing_rules(primary, supplement),
            [
                Rule("DOMAIN-SUFFIX", "example.com"),
                Rule("IP-CIDR", "192.0.2.0/24"),
                Rule("DOMAIN-SUFFIX", "new.example"),
            ],
        )

    def test_ip_variant_does_not_receive_domain_supplements(self) -> None:
        supplement = [
            Rule("DOMAIN-SUFFIX", "netflix.com"),
            Rule("IP-CIDR", "192.0.2.0/24"),
        ]

        self.assertEqual(
            _supplements_for_variant("Netflix_IP", supplement),
            [Rule("IP-CIDR", "192.0.2.0/24")],
        )

    def test_gemini_supplement_resolves_recursive_include(self) -> None:
        content = {
            "data/google-gemini": "include:google-deepmind\n",
            "data/google-deepmind": (
                "gemini.google.com\n"
                "notebooklm.google\n"
                "jules.google\n"
                "flow.google\n"
                "opal.google\n"
                "stitch.withgoogle.com\n"
                "antigravity.google\n"
                "full:cloudaicompanion.googleapis.com\n"
            ),
        }

        def fetcher(url: str) -> str:
            return next(
                text for path, text in content.items() if url.endswith(path)
            )

        rules, entries = build_service_supplements(
            self.catalog, "Gemini", fetcher=fetcher
        )

        self.assertIn(Rule("DOMAIN-SUFFIX", "notebooklm.google"), rules)
        self.assertIn(Rule("DOMAIN-SUFFIX", "jules.google"), rules)
        self.assertIn(Rule("DOMAIN-SUFFIX", "flow.google"), rules)
        self.assertIn(Rule("DOMAIN-SUFFIX", "opal.google"), rules)
        self.assertIn(Rule("DOMAIN-SUFFIX", "stitch.withgoogle.com"), rules)
        self.assertIn(Rule("DOMAIN-SUFFIX", "antigravity.google"), rules)
        self.assertIn(
            Rule("DOMAIN", "cloudaicompanion.googleapis.com"), rules
        )
        self.assertEqual(len(entries), 2)

    def test_grok_is_published_without_renaming_existing_services(self) -> None:
        artifact = build_target_artifact(
            self.catalog,
            "Grok",
            "singbox",
            fetcher=lambda _: "grok.com\ngrok.x.com\nx.ai\n",
        )

        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertEqual(artifact.service, "Grok")
        self.assertEqual(artifact.primary_variant_name, "Grok")
        self.assertEqual(
            artifact.rules,
            [
                Rule("DOMAIN-SUFFIX", "grok.com"),
                Rule("DOMAIN-SUFFIX", "grok.x.com"),
                Rule("DOMAIN-SUFFIX", "x.ai"),
            ],
        )
        self.assertIn("Twitter", self.catalog.services)
        self.assertIn("Gemini", self.catalog.services)
        self.assertEqual(
            self.catalog.bundles["x-full"].services, ["Twitter", "Grok"]
        )

    def test_self_maintained_feishu_keeps_ips_and_adds_missing_domains(self) -> None:
        artifact = build_target_artifact(
            self.catalog,
            "Feishu",
            "singbox",
            fetcher=lambda _: "feishu.cn\nnew-feishu.example\n",
        )

        self.assertIsNotNone(artifact)
        assert artifact is not None
        self.assertIn(Rule("DOMAIN-SUFFIX", "new-feishu.example"), artifact.rules)
        self.assertTrue(
            any(rule.type == "IP-CIDR" for rule in artifact.rules)
        )


if __name__ == "__main__":
    unittest.main()
