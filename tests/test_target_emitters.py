from __future__ import annotations

import importlib
import json
import unittest

from egloon_rule_hub.model.rules import Rule


def _load_renderer(module_name: str, function_name: str):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise AssertionError(f"missing emitter module: {module_name}") from exc
    renderer = getattr(module, function_name, None)
    if not callable(renderer):
        raise AssertionError(f"missing emitter function: {function_name}")
    return renderer


class SurfboardEmitterTests(unittest.TestCase):
    def test_renders_documented_rule_types_and_normalizes_aliases(self) -> None:
        render = _load_renderer(
            "egloon_rule_hub.emitters.surfboard", "render_surfboard_rules"
        )
        rules = [
            Rule("HOST", "api.example.com"),
            Rule("HOST-SUFFIX", "example.com"),
            Rule("HOST-KEYWORD", "example"),
            Rule("IP6-CIDR", "2001:db8::/32,no-resolve"),
            Rule("USER-AGENT", "Example*"),
            Rule("IP-ASN", "64512"),
            Rule("DOMAIN-REGEX", r"^api\\.example\\.com$"),
        ]

        self.assertEqual(
            render(rules),
            "DOMAIN,api.example.com\n"
            "DOMAIN-SUFFIX,example.com\n"
            "DOMAIN-KEYWORD,example\n"
            "IP-CIDR6,2001:db8::/32\n"
            "USER-AGENT,Example*\n",
        )


class SingBoxEmitterTests(unittest.TestCase):
    def test_renders_version_one_headless_rules_without_and_semantics(self) -> None:
        render = _load_renderer(
            "egloon_rule_hub.emitters.singbox", "render_singbox_rule_set"
        )
        rules = [
            Rule("DOMAIN", "api.example.com"),
            Rule("HOST-SUFFIX", "example.com"),
            Rule("DOMAIN-KEYWORD", "example"),
            Rule("DOMAIN-REGEX", r"^api\\.example\\.com$"),
            Rule("IP-CIDR", "192.0.2.0/24,no-resolve"),
            Rule("IP6-CIDR", "2001:db8::/32"),
            Rule("USER-AGENT", "Example*"),
            Rule("IP-ASN", "64512"),
            Rule("GEOIP", "US"),
        ]

        payload = json.loads(render(rules))

        self.assertEqual(payload["version"], 1)
        self.assertEqual(
            payload["rules"],
            [
                {"domain": ["api.example.com"]},
                {"domain_suffix": ["example.com"]},
                {"domain_keyword": ["example"]},
                {"domain_regex": [r"^api\\.example\\.com$"]},
                {"ip_cidr": ["192.0.2.0/24", "2001:db8::/32"]},
            ],
        )


if __name__ == "__main__":
    unittest.main()
