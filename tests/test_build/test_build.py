from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.build import build_service_rules, render_rule_artifacts
from egloon_rule_hub.model.catalog import (
    BundleDef,
    Catalog,
    ServiceDef,
    SourceDef,
    SourceRef,
    TargetDef,
)
from egloon_rule_hub.model.rules import Rule


class BuildPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "overrides" / "services").mkdir(parents=True, exist_ok=True)

        clash_path = self.root / "openai-clash.yaml"
        clash_path.write_text(
            "payload:\n"
            "  - DOMAIN,openai.com\n"
            "  - DOMAIN-SUFFIX,chatgpt.com\n",
            encoding="utf-8",
        )

        loon_path = self.root / "openai-loon.list"
        loon_path.write_text(
            "DOMAIN,openai.com\n"
            "DOMAIN,claude.ai\n",
            encoding="utf-8",
        )

        override_path = self.root / "overrides" / "services" / "OpenAI.yaml"
        override_path.write_text(
            "append:\n"
            "  - type: DOMAIN-SUFFIX\n"
            "    value: added.example\n"
            "remove:\n"
            "  - type: DOMAIN\n"
            "    value: claude.ai\n"
            "disable: []\n",
            encoding="utf-8",
        )

        self.catalog = Catalog(
            root=self.root,
            sources={
                "fixture": SourceDef(name="fixture", kind="remote"),
            },
            targets={
                "egern": TargetDef(name="egern", enabled=True, file_ext="yaml"),
                "loon": TargetDef(name="loon", enabled=True, file_ext="list"),
                "clash": TargetDef(name="clash", enabled=True, file_ext="yaml"),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    sources=[
                        SourceRef(
                            source="fixture",
                            url=clash_path.as_uri(),
                            format="clash_yaml",
                            priority=100,
                        ),
                        SourceRef(
                            source="fixture",
                            url=loon_path.as_uri(),
                            format="loon_list",
                            priority=90,
                        ),
                    ],
                    override="overrides/services/OpenAI.yaml",
                    notes="AI service",
                ),
                "Claude": ServiceDef(
                    name="Claude",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    sources=[],
                    override=None,
                    notes="AI service",
                ),
            },
            bundles={
                "ai": BundleDef(
                    name="ai",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    services=["OpenAI", "Claude"],
                )
            },
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_service_rules_merges_sources_and_overrides(self) -> None:
        rules = build_service_rules(self.catalog, "OpenAI")

        self.assertEqual(
            [(rule.type, rule.value) for rule in rules],
            [
                ("DOMAIN", "openai.com"),
                ("DOMAIN-SUFFIX", "chatgpt.com"),
                ("DOMAIN-SUFFIX", "added.example"),
            ],
        )

    def test_render_rule_artifacts_writes_service_and_bundle_outputs(self) -> None:
        service_rules = {
            "OpenAI": build_service_rules(self.catalog, "OpenAI"),
            "Claude": [],
        }

        render_rule_artifacts(self.root, self.catalog, service_rules)

        self.assertTrue(
            (self.root / "Rule" / "Loon" / "OpenAI" / "OpenAI.list").exists()
        )
        self.assertTrue(
            (self.root / "Rule" / "Clash" / "OpenAI" / "OpenAI.yaml").exists()
        )
        self.assertTrue(
            (self.root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml").exists()
        )
        self.assertTrue((self.root / "dist" / "bundles" / "ai" / "loon.list").exists())

        loon_bundle = (self.root / "dist" / "bundles" / "ai" / "loon.list").read_text(
            encoding="utf-8"
        )
        self.assertIn("DOMAIN,openai.com", loon_bundle)
        self.assertIn("DOMAIN-SUFFIX,chatgpt.com", loon_bundle)

    def test_render_rule_artifacts_requires_target_display_name(self) -> None:
        simple_catalog = Catalog(
            root=self.root,
            sources={},
            targets={
                "unknown": TargetDef(name="unknown", enabled=True, file_ext="yaml"),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["unknown"],
                    sources=[],
                    override=None,
                    notes="",
                )
            },
            bundles={},
        )
        with self.assertRaises(ValueError):
            render_rule_artifacts(
                self.root,
                simple_catalog,
                {"OpenAI": [Rule(type="DOMAIN", value="example.com")]},
            )


if __name__ == "__main__":
    unittest.main()
