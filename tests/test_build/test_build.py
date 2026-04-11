from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.build import (
    build_all_target_artifacts,
    build_service_rules,
    render_rule_artifacts,
    render_target_artifacts,
)
from egloon_rule_hub.model.catalog import (
    BundleDef,
    Catalog,
    ServiceDef,
    ServiceOrigin,
    ServiceTargetDef,
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

        shadowrocket_path = self.root / "openai-shadowrocket.list"
        shadowrocket_path.write_text(
            "# > OpenAI\n"
            "DOMAIN,shadowrocket.example\n",
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

        self.target_first_catalog = Catalog(
            root=self.root,
            sources={
                "fixture": SourceDef(name="fixture", kind="remote"),
            },
            targets={
                "egern": TargetDef(name="egern", enabled=True, file_ext="yaml"),
                "loon": TargetDef(
                    name="loon", enabled=True, file_ext="lsr", publish_mode="lsr"
                ),
                "clash": TargetDef(name="clash", enabled=True, file_ext="yaml"),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    target_sources={
                        "egern": ServiceTargetDef(
                            name="egern",
                            families={
                                "native": [],
                                "shadowrocket": [
                                    SourceRef(
                                        source="fixture",
                                        url=shadowrocket_path.as_uri(),
                                        format="shadowrocket_list",
                                        priority=100,
                                    )
                                ],
                                "clash": [
                                    SourceRef(
                                        source="fixture",
                                        url=clash_path.as_uri(),
                                        format="clash_yaml",
                                        priority=90,
                                    )
                                ],
                            },
                        ),
                        "loon": ServiceTargetDef(
                            name="loon",
                            families={
                                "native": [
                                    SourceRef(
                                        source="fixture",
                                        url=loon_path.as_uri(),
                                        format="loon_list",
                                        priority=100,
                                    )
                                ],
                                "shadowrocket": [],
                                "clash": [],
                            },
                        ),
                        "clash": ServiceTargetDef(
                            name="clash",
                            families={
                                "native": [
                                    SourceRef(
                                        source="fixture",
                                        url=clash_path.as_uri(),
                                        format="clash_yaml",
                                        priority=100,
                                    )
                                ],
                                "shadowrocket": [],
                                "clash": [],
                            },
                        ),
                    },
                    notes="AI service",
                ),
            },
            bundles={
                "ai": BundleDef(
                    name="ai",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    services=["OpenAI"],
                )
            },
            default_fallback_order=["native", "shadowrocket", "clash"],
        )

        self.self_maintained_catalog = Catalog(
            root=self.root,
            sources={},
            targets={
                "egern": TargetDef(name="egern", enabled=True, file_ext="yaml"),
                "loon": TargetDef(name="loon", enabled=True, file_ext="list"),
                "clash": TargetDef(name="clash", enabled=True, file_ext="yaml"),
            },
            services={
                "TXTService": ServiceDef(
                    name="TXTService",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    origin=ServiceOrigin(
                        kind="self_maintained",
                        source_path="Source/TXT/TXTService.txt",
                        source_url="https://example.com/txt-service",
                        source_note="txt-backed service",
                    ),
                ),
            },
            bundles={},
            self_maintained_rules={
                "TXTService": [
                    Rule(type="DOMAIN", value="txt.example"),
                    Rule(type="DOMAIN-SUFFIX", value="txt-suffix.example"),
                ]
            },
        )

        self.self_maintained_empty_rules_catalog = Catalog(
            root=self.root,
            sources={},
            targets={
                "egern": TargetDef(name="egern", enabled=True, file_ext="yaml"),
                "loon": TargetDef(name="loon", enabled=True, file_ext="list"),
                "clash": TargetDef(name="clash", enabled=True, file_ext="yaml"),
            },
            services={
                "TXTEmpty": ServiceDef(
                    name="TXTEmpty",
                    enabled=True,
                    targets=["egern", "loon", "clash"],
                    origin=ServiceOrigin(
                        kind="self_maintained",
                        source_path="Source/TXT/TXTEmpty.txt",
                    ),
                ),
            },
            bundles={},
            self_maintained_rules={"TXTEmpty": []},
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

    def test_render_rule_artifacts_prunes_legacy_dist_targets(self) -> None:
        legacy_target_dir = self.root / "dist" / "egern"
        legacy_target_dir.mkdir(parents=True, exist_ok=True)
        (legacy_target_dir / "OpenAI.yaml").write_text("legacy", encoding="utf-8")

        service_rules = {
            "OpenAI": build_service_rules(self.catalog, "OpenAI"),
            "Claude": [],
        }

        render_rule_artifacts(self.root, self.catalog, service_rules)

        self.assertFalse(legacy_target_dir.exists())
        self.assertTrue(
            (self.root / "dist" / "bundles" / "ai" / "loon.list").exists()
        )

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

    def test_build_all_target_artifacts_selects_strict_family_per_target(self) -> None:
        artifacts = build_all_target_artifacts(self.target_first_catalog)

        egern = artifacts["OpenAI"]["egern"]
        self.assertEqual(egern.selected_family, "shadowrocket")
        self.assertEqual(
            [(rule.type, rule.value) for rule in egern.rules],
            [("DOMAIN", "shadowrocket.example")],
        )

        loon = artifacts["OpenAI"]["loon"]
        self.assertEqual(loon.selected_family, "native")
        self.assertIn(("DOMAIN", "openai.com"), [(rule.type, rule.value) for rule in loon.rules])
        self.assertNotIn(
            ("DOMAIN", "shadowrocket.example"),
            [(rule.type, rule.value) for rule in loon.rules],
        )

        clash = artifacts["OpenAI"]["clash"]
        self.assertEqual(clash.selected_family, "native")
        self.assertIn(
            ("DOMAIN-SUFFIX", "chatgpt.com"),
            [(rule.type, rule.value) for rule in clash.rules],
        )

    def test_render_target_artifacts_writes_selected_target_and_bundle_outputs(self) -> None:
        artifacts = build_all_target_artifacts(self.target_first_catalog)

        render_target_artifacts(self.root, self.target_first_catalog, artifacts)

        self.assertTrue(
            (self.root / "Rule" / "Shadowrocket" / "OpenAI" / "OpenAI.list").exists()
            is False
        )
        self.assertTrue(
            (self.root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml").exists()
        )
        self.assertEqual(
            (self.root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml").read_text(encoding="utf-8"),
            "domain_set:\n- shadowrocket.example\n",
        )
        self.assertIn(
            "shadowrocket.example",
            (self.root / "dist" / "bundles" / "ai" / "egern.yaml").read_text(
                encoding="utf-8"
            ),
        )

    def test_render_target_artifacts_prunes_stale_loon_ext_outputs(self) -> None:
        artifacts = build_all_target_artifacts(self.target_first_catalog)
        stale_service_output = self.root / "Rule" / "Loon" / "OpenAI" / "OpenAI.list"
        stale_service_output.parent.mkdir(parents=True, exist_ok=True)
        stale_service_output.write_text("stale service list", encoding="utf-8")
        fresh_service_unrelated = self.root / "Rule" / "Loon" / "Claude" / "Claude.list"
        fresh_service_unrelated.parent.mkdir(parents=True, exist_ok=True)
        fresh_service_unrelated.write_text("keep me", encoding="utf-8")

        stale_bundle_output = self.root / "dist" / "bundles" / "ai" / "loon.list"
        stale_bundle_output.parent.mkdir(parents=True, exist_ok=True)
        stale_bundle_output.write_text("stale bundle list", encoding="utf-8")
        unrelated_bundle_output = self.root / "dist" / "bundles" / "social" / "loon.list"
        unrelated_bundle_output.parent.mkdir(parents=True, exist_ok=True)
        unrelated_bundle_output.write_text("keep me too", encoding="utf-8")

        render_target_artifacts(self.root, self.target_first_catalog, artifacts)

        self.assertFalse(stale_service_output.exists())
        self.assertTrue((self.root / "Rule" / "Loon" / "OpenAI" / "OpenAI.lsr").exists())
        self.assertTrue(fresh_service_unrelated.exists())
        self.assertFalse(stale_bundle_output.exists())
        self.assertTrue((self.root / "dist" / "bundles" / "ai" / "loon.lsr").exists())
        self.assertTrue(unrelated_bundle_output.exists())

    def test_build_all_target_artifacts_self_maintained_emits_all_targets(self) -> None:
        artifacts = build_all_target_artifacts(self.self_maintained_catalog)

        self.assertIn("TXTService", artifacts)
        self.assertEqual(set(artifacts["TXTService"].keys()), {"egern", "loon", "clash"})
        for target_name in ("egern", "loon", "clash"):
            artifact = artifacts["TXTService"][target_name]
            self.assertEqual(
                [(rule.type, rule.value) for rule in artifact.rules],
                [
                    ("DOMAIN", "txt.example"),
                    ("DOMAIN-SUFFIX", "txt-suffix.example"),
                ],
            )
            self.assertEqual(artifact.selected_family, "self_maintained")
            self.assertEqual(artifact.selected_native_target, target_name)
            self.assertTrue(artifact.is_native)
            self.assertFalse(artifact.is_converted)

    def test_build_all_target_artifacts_self_maintained_includes_origin_metadata(self) -> None:
        artifacts = build_all_target_artifacts(self.self_maintained_catalog)
        egern_artifact = artifacts["TXTService"]["egern"]

        self.assertEqual(egern_artifact.origin_kind, "self_maintained")
        self.assertEqual(
            egern_artifact.origin_source_path,
            "Source/TXT/TXTService.txt",
        )
        self.assertEqual(
            egern_artifact.origin_source_url,
            "https://example.com/txt-service",
        )

    def test_build_all_target_artifacts_self_maintained_skips_empty_rule_services(self) -> None:
        artifacts = build_all_target_artifacts(self.self_maintained_empty_rules_catalog)

        self.assertNotIn("TXTEmpty", artifacts)

    def test_render_target_artifacts_self_maintained_writes_outputs(self) -> None:
        artifacts = build_all_target_artifacts(self.self_maintained_catalog)

        render_target_artifacts(self.root, self.self_maintained_catalog, artifacts)

        self.assertTrue(
            (self.root / "Rule" / "Loon" / "TXTService" / "TXTService.list").exists()
        )
        self.assertIn(
            "DOMAIN,txt.example",
            (self.root / "Rule" / "Loon" / "TXTService" / "TXTService.list").read_text(
                encoding="utf-8"
            ),
        )

    def test_render_target_artifacts_self_maintained_prunes_stale_outputs_after_empty_transition(
        self,
    ) -> None:
        initial_artifacts = build_all_target_artifacts(self.self_maintained_catalog)
        render_target_artifacts(self.root, self.self_maintained_catalog, initial_artifacts)
        output_path = self.root / "Rule" / "Loon" / "TXTService" / "TXTService.list"
        self.assertTrue(output_path.exists())

        self.self_maintained_catalog.self_maintained_rules["TXTService"] = []
        empty_artifacts = build_all_target_artifacts(self.self_maintained_catalog)
        render_target_artifacts(self.root, self.self_maintained_catalog, empty_artifacts)

        self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
