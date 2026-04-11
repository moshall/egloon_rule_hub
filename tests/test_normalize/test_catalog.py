from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from egloon_rule_hub.docs.render import write_markdown_docs
from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
    ServiceOrigin,
    ServiceTargetDef,
    ServiceTargetVariantDef,
    SourceDef,
    SourceRef,
    TargetDef,
    load_catalog,
)
from egloon_rule_hub.normalize.dedupe import dedupe_rules
from egloon_rule_hub.normalize.merge import merge_rule_streams
from egloon_rule_hub.model.rules import Rule


class CatalogTests(unittest.TestCase):
    def test_load_catalog(self) -> None:
        root = Path(__file__).resolve().parents[2]
        catalog = load_catalog(root)
        self.assertIn("OpenAI", catalog.services)
        self.assertIn("China", catalog.services)
        self.assertIn("ai", catalog.bundles)
        self.assertIn("egern", catalog.targets)
        self.assertIn("blackmatrix7", catalog.sources)
        self.assertEqual(catalog.targets["loon"].publish_mode, "lsr")
        self.assertIn("clash", catalog.services["OpenAI"].target_sources)
        self.assertIn("native", catalog.services["OpenAI"].target_sources["clash"].families)
        self.assertEqual(
            set(catalog.services["China"].target_sources["loon"].variants),
            {"China", "China_Domain", "China_Resolve"},
        )
        self.assertTrue(catalog.services["China"].target_sources["loon"].variants["China"].primary)
        self.assertEqual(
            catalog.services["OpenAI"].target_sources["egern"].selected_order(
                catalog.services["OpenAI"].fallback_order,
                catalog.default_fallback_order,
            ),
            ["native", "shadowrocket", "clash"],
        )

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
        fixture_root = Path(__file__).resolve().parents[2]
        catalog = load_catalog(fixture_root)
        with tempfile.TemporaryDirectory() as temp_root:
            output_root = Path(temp_root)
            write_markdown_docs(output_root, catalog)
            attribution = (output_root / "docs" / "attribution.md").read_text(
                encoding="utf-8"
            )
        self.assertIn("# Attribution", attribution)
        self.assertIn("blackmatrix7", attribution)
        self.assertIn("ACL4SSR", attribution)

    def test_load_target_first_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  loon:\n"
                "    enabled: true\n"
                "    file_ext: lsr\n"
                "    publish_mode: lsr\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  egern:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "defaults:\n"
                "  fallback_order: [native, shadowrocket, clash]\n"
                "services:\n"
                "  OpenAI:\n"
                "    enabled: true\n"
                "    outputs: [loon, clash, egern]\n"
                "    target_sources:\n"
                "      loon:\n"
                "        native:\n"
                "          - source: sample\n"
                "            url: https://example.com/rule/Loon/OpenAI/OpenAI.list\n"
                "            format: loon_list\n"
                "      clash:\n"
                "        native:\n"
                "          - source: sample\n"
                "            url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n"
                "            format: clash_yaml\n"
                "      egern:\n"
                "        native: []\n"
                "        shadowrocket: []\n"
                "        clash:\n"
                "          - source: sample\n"
                "            url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n"
                "            format: clash_yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text(
                "bundles:\n"
                "  ai:\n"
                "    enabled: true\n"
                "    targets: [loon, clash, egern]\n"
                "    services: [OpenAI]\n",
                encoding="utf-8",
            )

            catalog = load_catalog(root)

        self.assertEqual(catalog.targets["loon"].publish_mode, "lsr")
        self.assertEqual(catalog.services["OpenAI"].outputs, ["loon", "clash", "egern"])
        self.assertIn("native", catalog.services["OpenAI"].target_sources["loon"].families)
        self.assertIn("clash", catalog.services["OpenAI"].target_sources["egern"].families)

    def test_load_catalog_normalizes_variant_targets_and_single_variant_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  loon:\n"
                "    enabled: true\n"
                "    file_ext: lsr\n"
                "    publish_mode: lsr\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "defaults:\n"
                "  fallback_order: [native, shadowrocket, clash]\n"
                "services:\n"
                "  China:\n"
                "    enabled: true\n"
                "    outputs: [loon]\n"
                "    target_sources:\n"
                "      loon:\n"
                "        variants:\n"
                "          China:\n"
                "            primary: true\n"
                "            native:\n"
                "              - source: sample\n"
                "                url: https://example.com/rule/Loon/China/China.list\n"
                "                format: loon_list\n"
                "          China_Domain:\n"
                "            primary: false\n"
                "            native:\n"
                "              - source: sample\n"
                "                url: https://example.com/rule/Loon/China/China_Domain.list\n"
                "                format: loon_list\n"
                "          China_Resolve:\n"
                "            primary: false\n"
                "            native:\n"
                "              - source: sample\n"
                "                url: https://example.com/rule/Loon/China/China_Resolve.list\n"
                "                format: loon_list\n"
                "  OpenAI:\n"
                "    enabled: true\n"
                "    outputs: [clash]\n"
                "    target_sources:\n"
                "      clash:\n"
                "        native:\n"
                "          - source: sample\n"
                "            url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n"
                "            format: clash_yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text("bundles: {}\n", encoding="utf-8")

            catalog = load_catalog(root)

        china_target = catalog.services["China"].target_sources["loon"]
        self.assertEqual(set(china_target.variants), {"China", "China_Domain", "China_Resolve"})
        self.assertTrue(china_target.variants["China"].primary)
        self.assertFalse(china_target.variants["China_Domain"].primary)
        self.assertEqual(
            china_target.variants["China_Domain"].families["native"][0].url,
            "https://example.com/rule/Loon/China/China_Domain.list",
        )

        openai_target = catalog.services["OpenAI"].target_sources["clash"]
        self.assertEqual(list(openai_target.variants), ["OpenAI"])
        self.assertTrue(openai_target.variants["OpenAI"].primary)

    def test_write_markdown_docs_lists_variant_files_and_upstream_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog = Catalog(
                root=root,
                sources={"sample": SourceDef(name="sample", kind="remote")},
                targets={
                    "loon": TargetDef(name="loon", enabled=True, file_ext="lsr", publish_mode="lsr"),
                },
                services={
                    "China": ServiceDef(
                        name="China",
                        enabled=True,
                        targets=["loon"],
                        target_sources={
                            "loon": ServiceTargetDef(
                                name="loon",
                                variants={
                                    "China": ServiceTargetVariantDef(
                                        name="China",
                                        primary=True,
                                        families={"native": [], "shadowrocket": [], "clash": []},
                                    ),
                                    "China_Domain": ServiceTargetVariantDef(
                                        name="China_Domain",
                                        primary=False,
                                        families={"native": [], "shadowrocket": [], "clash": []},
                                    ),
                                    "China_Resolve": ServiceTargetVariantDef(
                                        name="China_Resolve",
                                        primary=False,
                                        families={"native": [], "shadowrocket": [], "clash": []},
                                    ),
                                },
                            )
                        },
                    )
                },
                bundles={},
            )

            manifest_path = root / "dist" / "manifests" / "upstream_docs.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "China": [
                            {
                                "target": "loon",
                                "target_dir": "Loon",
                                "service": "China",
                                "variant": "China",
                                "variant_primary": True,
                                "variant_file": "China.lsr",
                                "source": "sample",
                                "priority": 100,
                                "rule_url": "https://example.com/rule/Loon/China/China.list",
                                "readme_url": "https://example.com/rule/Loon/China/README.md",
                                "status": "ok",
                                "snapshot_path": None,
                                "entry_key": "china",
                                "is_converted": False,
                            },
                            {
                                "target": "loon",
                                "target_dir": "Loon",
                                "service": "China",
                                "variant": "China_Domain",
                                "variant_primary": False,
                                "variant_file": "China_Domain.lsr",
                                "source": "sample",
                                "priority": 100,
                                "rule_url": "https://example.com/rule/Loon/China/China_Domain.list",
                                "readme_url": "https://example.com/rule/Loon/China/README.md",
                                "status": "ok",
                                "snapshot_path": None,
                                "entry_key": "china-domain",
                                "is_converted": False,
                            },
                            {
                                "target": "loon",
                                "target_dir": "Loon",
                                "service": "China",
                                "variant": "China_Resolve",
                                "variant_primary": False,
                                "variant_file": "China_Resolve.lsr",
                                "source": "sample",
                                "priority": 100,
                                "rule_url": "https://example.com/rule/Loon/China/China_Resolve.list",
                                "readme_url": "https://example.com/rule/Loon/China/README.md",
                                "status": "ok",
                                "snapshot_path": None,
                                "entry_key": "china-resolve",
                                "is_converted": False,
                            },
                        ]
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

            write_markdown_docs(root, catalog)
            readme = (root / "Rule" / "Loon" / "China" / "README.md").read_text(
                encoding="utf-8"
            )

        self.assertIn("China_Domain.lsr", readme)
        self.assertIn("./China_Domain.lsr", readme)
        self.assertIn("China_Resolve", readme)
        self.assertIn("rule/Loon/China/China_Domain.list", readme)

    def test_load_target_first_catalog_rejects_unknown_family(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "services:\n"
                "  OpenAI:\n"
                "    enabled: true\n"
                "    outputs: [clash]\n"
                "    target_sources:\n"
                "      clash:\n"
                "        invalid_family:\n"
                "          - source: sample\n"
                "            url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n"
                "            format: clash_yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text(
                "bundles: {}\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                load_catalog(root)

    def test_load_catalog_injects_self_maintained_txt_services(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            txt_dir = root / "Source" / "TXT"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  egern:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  loon:\n"
                "    enabled: true\n"
                "    file_ext: lsr\n"
                "    publish_mode: lsr\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  quanx:\n"
                "    enabled: true\n"
                "    file_ext: conf\n"
                "  shadowrocket:\n"
                "    enabled: true\n"
                "    file_ext: conf\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "services:\n"
                "  OpenAI:\n"
                "    enabled: true\n"
                "    outputs: [clash]\n"
                "    sources:\n"
                "      - source: sample\n"
                "        url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text("bundles: {}\n", encoding="utf-8")

            (txt_dir / "Feishu.txt").write_text(
                "# @source_url: https://www.feishu.cn/hc/zh-CN/articles/360044683233\n"
                "# @source_note: Feishu official help center\n"
                "# @generated_by: refresh_feishu_txt\n"
                "DOMAIN-SUFFIX,feishu.cn\n"
                "IP-CIDR,1.1.1.0/24\n",
                encoding="utf-8",
            )
            (txt_dir / "IyfTv.txt").write_text(
                "# @source_url: https://github.com/example/manual\n"
                "iyf.tv\n"
                "DOMAIN-SUFFIX,yfsp.tv\n",
                encoding="utf-8",
            )

            catalog = load_catalog(root)

        self.assertIn("OpenAI", catalog.services)
        self.assertIn("Feishu", catalog.services)
        self.assertIn("IyfTv", catalog.services)
        self.assertEqual(
            catalog.services["IyfTv"].targets,
            ["egern", "loon", "clash", "quanx", "shadowrocket"],
        )
        self.assertEqual(catalog.services["Feishu"].origin.kind, "self_maintained")
        self.assertEqual(
            catalog.services["Feishu"].origin.source_path, "Source/TXT/Feishu.txt"
        )
        self.assertEqual(
            catalog.services["Feishu"].origin.source_url,
            "https://www.feishu.cn/hc/zh-CN/articles/360044683233",
        )
        self.assertEqual(
            catalog.services["Feishu"].origin.source_note,
            "Feishu official help center",
        )
        self.assertEqual(
            catalog.services["Feishu"].origin.generated_by, "refresh_feishu_txt"
        )
        self.assertIn("Feishu", catalog.self_maintained_rules)
        self.assertIn("IyfTv", catalog.self_maintained_rules)
        self.assertEqual(
            [(rule.type, rule.value) for rule in catalog.self_maintained_rules["Feishu"]],
            [("DOMAIN-SUFFIX", "feishu.cn"), ("IP-CIDR", "1.1.1.0/24")],
        )
        self.assertEqual(
            [(rule.type, rule.value) for rule in catalog.self_maintained_rules["IyfTv"]],
            [("DOMAIN-SUFFIX", "iyf.tv"), ("DOMAIN-SUFFIX", "yfsp.tv")],
        )

    def test_load_catalog_records_txt_discovery_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            catalog_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "services:\n"
                "  OpenAI:\n"
                "    enabled: true\n"
                "    outputs: [clash]\n"
                "    sources:\n"
                "      - source: sample\n"
                "        url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text("bundles: {}\n", encoding="utf-8")

            with patch(
                "egloon_rule_hub.model.catalog.discover_txt_services",
                side_effect=ValueError("failed to parse TXT service"),
            ):
                catalog = load_catalog(root)

        self.assertIn("OpenAI", catalog.services)
        self.assertEqual(
            catalog.self_maintained_failures["Source/TXT"],
            "failed to parse TXT service",
        )
        self.assertEqual(catalog.self_maintained_rules, {})

    def test_load_catalog_skips_txt_conflict_with_yaml_service(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            txt_dir = root / "Source" / "TXT"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text(
                "sources:\n"
                "  sample:\n"
                "    kind: remote\n",
                encoding="utf-8",
            )
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  egern:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  loon:\n"
                "    enabled: true\n"
                "    file_ext: lsr\n"
                "  quanx:\n"
                "    enabled: true\n"
                "    file_ext: conf\n"
                "  shadowrocket:\n"
                "    enabled: true\n"
                "    file_ext: conf\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text(
                "services:\n"
                "  Feishu:\n"
                "    enabled: true\n"
                "    outputs: [clash]\n"
                "    sources:\n"
                "      - source: sample\n"
                "        url: https://example.com/rule/Clash/Feishu/Feishu.yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "bundles.yaml").write_text("bundles: {}\n", encoding="utf-8")
            (txt_dir / "Feishu.txt").write_text(
                "DOMAIN-SUFFIX,feishu.cn\n",
                encoding="utf-8",
            )

            catalog = load_catalog(root)

        self.assertEqual(catalog.services["Feishu"].targets, ["clash"])
        self.assertEqual(catalog.services["Feishu"].origin.kind, "upstream")
        self.assertNotIn("Feishu", catalog.self_maintained_rules)
        self.assertIn("Source/TXT/Feishu.txt", catalog.self_maintained_failures)
        self.assertIn(
            "conflicts with existing YAML service",
            catalog.self_maintained_failures["Source/TXT/Feishu.txt"],
        )

    def test_load_catalog_validates_static_yaml_before_txt_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            txt_dir = root / "Source" / "TXT"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text("sources: {}\n", encoding="utf-8")
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text("services: {}\n", encoding="utf-8")
            (catalog_dir / "bundles.yaml").write_text(
                "bundles:\n"
                "  bad:\n"
                "    enabled: true\n"
                "    targets: [clash]\n"
                "    services: [IyfTv]\n",
                encoding="utf-8",
            )
            (txt_dir / "IyfTv.txt").write_text("DOMAIN-SUFFIX,iyf.tv\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_catalog(root)

    def test_load_catalog_injects_txt_targets_intersected_with_known_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            catalog_dir = root / "catalog"
            txt_dir = root / "Source" / "TXT"
            catalog_dir.mkdir(parents=True, exist_ok=True)
            txt_dir.mkdir(parents=True, exist_ok=True)

            (catalog_dir / "sources.yaml").write_text("sources: {}\n", encoding="utf-8")
            (catalog_dir / "targets.yaml").write_text(
                "targets:\n"
                "  clash:\n"
                "    enabled: true\n"
                "    file_ext: yaml\n"
                "  shadowrocket:\n"
                "    enabled: true\n"
                "    file_ext: conf\n"
                "  surge:\n"
                "    enabled: true\n"
                "    file_ext: conf\n",
                encoding="utf-8",
            )
            (catalog_dir / "services.yaml").write_text("services: {}\n", encoding="utf-8")
            (catalog_dir / "bundles.yaml").write_text("bundles: {}\n", encoding="utf-8")
            (txt_dir / "IyfTv.txt").write_text("DOMAIN-SUFFIX,iyf.tv\n", encoding="utf-8")

            catalog = load_catalog(root)

        self.assertEqual(catalog.services["IyfTv"].targets, ["clash", "shadowrocket"])


class ServiceDocsRenderTests(unittest.TestCase):
    TARGET_CLASH = "clash"
    TARGET_CLASH_DIR = "Clash"
    TARGET_EGERN = "egern"
    TARGET_EGERN_DIR = "Egern"

    RULE_URL_PRIMARY = "https://example.com/rules/OpenAI/OpenAI.yaml"
    RULE_URL_SECONDARY = "https://mirror.example.net/rules/OpenAI/OpenAI.list"
    README_URL_PRIMARY = "https://example.com/rules/OpenAI/README.md"
    README_URL_SECONDARY = "https://mirror.example.net/rules/OpenAI/README.md"
    SNAPSHOT_PATH_PRIMARY = "dist/upstream-readmes/openai/fixture/README.md"
    SNAPSHOT_PATH_SECONDARY = "dist/upstream-readmes/openai/mirror/README.md"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.catalog = Catalog(
            root=self.root,
            sources={
                "fixture": SourceDef(name="fixture", kind="remote"),
                "mirror": SourceDef(name="mirror", kind="remote"),
            },
            targets={
                self.TARGET_CLASH: TargetDef(
                    name=self.TARGET_CLASH, enabled=True, file_ext="yaml"
                ),
                self.TARGET_EGERN: TargetDef(
                    name=self.TARGET_EGERN, enabled=True, file_ext="yaml"
                ),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=[self.TARGET_CLASH, self.TARGET_EGERN],
                    sources=[
                        SourceRef(
                            source="fixture",
                            url=self.RULE_URL_PRIMARY,
                            format="clash_yaml",
                            priority=100,
                        ),
                        SourceRef(
                            source="mirror",
                            url=self.RULE_URL_SECONDARY,
                            format="loon_list",
                            priority=200,
                        ),
                    ],
                    notes="AI service",
                )
            },
            bundles={},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_clash_readme_includes_native_target_and_snapshot(self) -> None:
        self._write_snapshot(
            self.SNAPSHOT_PATH_PRIMARY, "# README\n\nOriginal upstream text\n"
        )
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_CLASH,
                        status="ok",
                        snapshot_path=self.SNAPSHOT_PATH_PRIMARY,
                        is_converted=False,
                    )
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_CLASH_DIR, "OpenAI")
        self.assertIn("# OpenAI for Clash", readme)
        self.assertIn("direct upstream target", readme)
        self.assertIn("Selected source family: `native`", readme)
        self.assertIn("Upstream native target: `Clash`", readme)
        self.assertIn("Original upstream text", readme)
        self.assertIn(self.RULE_URL_PRIMARY, readme)
        self.assertIn(self.README_URL_PRIMARY, readme)

    def test_egern_readme_includes_converted_wording_and_missing_states(self) -> None:
        self._write_snapshot(self.SNAPSHOT_PATH_SECONDARY, "Converted upstream text\n")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_EGERN,
                        status="ok",
                        snapshot_path=self.SNAPSHOT_PATH_SECONDARY,
                        is_converted=True,
                    ),
                    self._manifest_entry(
                        target=self.TARGET_EGERN,
                        status="missing",
                        snapshot_path=None,
                        source="mirror",
                        is_converted=True,
                    ),
                    self._manifest_entry(
                        target=self.TARGET_EGERN,
                        status="fetch_error",
                        snapshot_path=None,
                        source="mirror",
                        is_converted=True,
                        entry_key="mirror-fetch_error",
                    ),
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_EGERN_DIR, "OpenAI")
        self.assertIn("generated by egloon_rule_hub", readme)
        self.assertIn("not a native upstream Egern artifact", readme)
        self.assertIn("Selected source family: `clash`", readme)
        self.assertIn("Upstream native target: `Clash`", readme)
        self.assertIn("Conversion path: `Clash -> Egern`", readme)
        self.assertEqual(readme.count("### Upstream Entry"), 3)
        self.assertIn("upstream README missing", readme)
        self.assertIn("upstream README fetch_error", readme)
        self.assertIn("Converted upstream text", readme)

    def test_service_index_links_to_target_readmes(self) -> None:
        self._write_snapshot(self.SNAPSHOT_PATH_PRIMARY, "Primary README\n")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_CLASH,
                        status="ok",
                        snapshot_path=self.SNAPSHOT_PATH_PRIMARY,
                        is_converted=False,
                    )
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        services_doc = (self.root / "docs" / "services.md").read_text(encoding="utf-8")
        self.assertIn("## Target READMEs", services_doc)
        self.assertIn("Rule/Clash/OpenAI/README.md", services_doc)
        self.assertNotIn("services/OpenAI.md", services_doc)

    def test_services_markdown_uses_distinct_target_source_count(self) -> None:
        duplicate_ref = SourceRef(
            source="fixture",
            url=self.RULE_URL_PRIMARY,
            format="clash_yaml",
            priority=100,
        )
        self.catalog.services["OpenAI"].sources = [duplicate_ref, duplicate_ref, duplicate_ref]
        self.catalog.services["OpenAI"].target_sources = {
            self.TARGET_CLASH: ServiceTargetDef(
                name=self.TARGET_CLASH,
                families={"native": [duplicate_ref], "shadowrocket": [], "clash": []},
            ),
            self.TARGET_EGERN: ServiceTargetDef(
                name=self.TARGET_EGERN,
                families={"native": [], "shadowrocket": [], "clash": [duplicate_ref]},
            ),
        }

        write_markdown_docs(self.root, self.catalog)

        services_doc = (self.root / "docs" / "services.md").read_text(encoding="utf-8")
        self.assertIn("| OpenAI | True | clash, egern | 1 | AI service |", services_doc)

    def test_self_maintained_target_readme_uses_catalog_origin_metadata_without_artifacts(
        self,
    ) -> None:
        self.catalog.services["Feishu"] = ServiceDef(
            name="Feishu",
            enabled=True,
            targets=[self.TARGET_CLASH],
            notes="Feishu official help center",
            origin=ServiceOrigin(
                kind="self_maintained",
                source_path="Source/TXT/Feishu.txt",
                source_url="https://www.feishu.cn/hc/zh-CN/articles/360044683233",
                source_note="Feishu official help center",
            ),
        )
        self.catalog.self_maintained_rules["Feishu"] = [
            Rule("DOMAIN-SUFFIX", "feishu.cn"),
        ]

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_CLASH_DIR, "Feishu")
        self.assertIn("# Feishu for Clash", readme)
        self.assertIn("self-maintained", readme)
        self.assertIn("https://www.feishu.cn/hc/zh-CN/articles/360044683233", readme)
        self.assertIn(
            "- TXT source: [Source/TXT/Feishu.txt](../../../Source/TXT/Feishu.txt)",
            readme,
        )
        self.assertNotIn("Selected source family", readme)
        self.assertNotIn("Upstream README Sources", readme)

    def test_self_maintained_docs_skip_disabled_targets_without_artifacts(self) -> None:
        self.catalog.targets[self.TARGET_CLASH].enabled = False
        self.catalog.services["Feishu"] = ServiceDef(
            name="Feishu",
            enabled=True,
            targets=[self.TARGET_CLASH],
            origin=ServiceOrigin(
                kind="self_maintained",
                source_path="Source/TXT/Feishu.txt",
            ),
        )
        self.catalog.self_maintained_rules["Feishu"] = [
            Rule("DOMAIN-SUFFIX", "feishu.cn"),
        ]

        write_markdown_docs(self.root, self.catalog)

        self.assertFalse((self.root / "Rule" / self.TARGET_CLASH_DIR / "Feishu").exists())
        services_doc = (self.root / "docs" / "services.md").read_text(encoding="utf-8")
        self.assertIn("- Feishu: (no target README yet)", services_doc)

    def test_self_maintained_docs_skip_empty_rule_services_without_artifacts(self) -> None:
        self.catalog.services["Empty"] = ServiceDef(
            name="Empty",
            enabled=True,
            targets=[self.TARGET_CLASH],
            origin=ServiceOrigin(
                kind="self_maintained",
                source_path="Source/TXT/Empty.txt",
            ),
        )
        self.catalog.self_maintained_rules["Empty"] = []

        write_markdown_docs(self.root, self.catalog)

        self.assertFalse((self.root / "Rule" / self.TARGET_CLASH_DIR / "Empty").exists())
        services_doc = (self.root / "docs" / "services.md").read_text(encoding="utf-8")
        self.assertIn("- Empty: (no target README yet)", services_doc)

    def test_write_markdown_docs_prunes_legacy_services_directory(self) -> None:
        legacy_file = self.root / "docs" / "services" / "OpenAI.md"
        legacy_file.parent.mkdir(parents=True, exist_ok=True)
        legacy_file.write_text("legacy", encoding="utf-8")

        write_markdown_docs(self.root, self.catalog)

        self.assertFalse((self.root / "docs" / "services").exists())
        self.assertTrue((self.root / "docs" / "services.md").exists())

    def test_write_markdown_docs_prunes_stale_target_readmes_and_empty_dirs(self) -> None:
        clash_dir = self.root / "Rule" / self.TARGET_CLASH_DIR / "OpenAI"
        clash_dir.mkdir(parents=True, exist_ok=True)
        (clash_dir / "README.md").write_text("stale clash", encoding="utf-8")
        (clash_dir / "OpenAI.yaml").write_text("artifact", encoding="utf-8")

        egern_dir = self.root / "Rule" / self.TARGET_EGERN_DIR / "OpenAI"
        egern_dir.mkdir(parents=True, exist_ok=True)
        (egern_dir / "README.md").write_text("stale egern", encoding="utf-8")

        self._write_upstream_manifest({})

        write_markdown_docs(self.root, self.catalog)

        self.assertFalse((clash_dir / "README.md").exists())
        self.assertTrue((clash_dir / "OpenAI.yaml").exists())
        self.assertTrue(clash_dir.exists())
        self.assertFalse(egern_dir.exists())
        self.assertFalse((self.root / "Rule" / self.TARGET_EGERN_DIR).exists())

    def test_usage_markdown_highlights_rule_directories(self) -> None:
        write_markdown_docs(self.root, self.catalog)
        usage_doc = (self.root / "docs" / "usage.md").read_text(encoding="utf-8")
        self.assertIn("Rule/Clash/OpenAI/OpenAI.yaml", usage_doc)
        self.assertIn("Rule/Loon/OpenAI/OpenAI.lsr", usage_doc)
        self.assertIn("Rule/Egern/OpenAI/OpenAI.yaml", usage_doc)
        self.assertNotIn("dist/clash/OpenAI", usage_doc)
        self.assertNotIn("dist/loon/OpenAI", usage_doc)

    def test_missing_target_dir_uses_native_display_name_mapping(self) -> None:
        self.catalog.targets["quanx"] = TargetDef(name="quanx", enabled=True, file_ext="list")
        self.catalog.targets["shadowrocket"] = TargetDef(
            name="shadowrocket", enabled=True, file_ext="list"
        )
        self.catalog.services["OpenAI"].targets.extend(["quanx", "shadowrocket"])
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        **self._manifest_entry(
                            target="quanx",
                            status="missing",
                            snapshot_path=None,
                            is_converted=True,
                            selected_family="native",
                            selected_native_target="quanx",
                            conversion_path=None,
                            publish_mode=None,
                            entry_key="quanx-missing",
                        ),
                        "target_dir": None,
                    },
                    {
                        **self._manifest_entry(
                            target="shadowrocket",
                            status="missing",
                            snapshot_path=None,
                            is_converted=True,
                            selected_family="native",
                            selected_native_target="shadowrocket",
                            conversion_path=None,
                            publish_mode=None,
                            entry_key="shadowrocket-missing",
                        ),
                        "target_dir": None,
                    },
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        self.assertTrue((self.root / "Rule" / "QuanX" / "OpenAI" / "README.md").exists())
        self.assertTrue(
            (self.root / "Rule" / "Shadowrocket" / "OpenAI" / "README.md").exists()
        )

    def test_traversal_style_snapshot_path_is_rejected(self) -> None:
        outside_file = self.root.parent / f"{self.root.name}-outside-README.md"
        outside_file.write_text("SHOULD NOT BE INLINED\n", encoding="utf-8")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_CLASH,
                        status="ok",
                        snapshot_path=f"../{outside_file.name}",
                        is_converted=False,
                    )
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_CLASH_DIR, "OpenAI")
        self.assertIn("upstream README missing snapshot", readme)
        self.assertNotIn("SHOULD NOT BE INLINED", readme)

    def test_snapshot_with_backticks_uses_safe_outer_code_fence(self) -> None:
        self._write_snapshot(
            self.SNAPSHOT_PATH_PRIMARY,
            "# README\n\n```bash\necho hi\n```\n",
        )
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_CLASH,
                        status="ok",
                        snapshot_path=self.SNAPSHOT_PATH_PRIMARY,
                        is_converted=False,
                    )
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_CLASH_DIR, "OpenAI")
        self.assertIn("````text", readme)
        self.assertIn("```bash", readme)
        self.assertIn("\n````\n", readme)

    def test_invalid_utf8_snapshot_bytes_render_as_missing_snapshot(self) -> None:
        self._write_snapshot_bytes(self.SNAPSHOT_PATH_PRIMARY, b"\xff\xfe\x80")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    self._manifest_entry(
                        target=self.TARGET_CLASH,
                        status="ok",
                        snapshot_path=self.SNAPSHOT_PATH_PRIMARY,
                        is_converted=False,
                    )
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        readme = self._read_target_readme(self.TARGET_CLASH_DIR, "OpenAI")
        self.assertIn("upstream README missing snapshot", readme)

    def _manifest_entry(
        self,
        *,
        target: str,
        status: str,
        is_converted: bool,
        selected_family: str | None = None,
        selected_native_target: str | None = None,
        conversion_path: str | None = None,
        publish_mode: str | None = None,
        snapshot_path: str | None = None,
        source: str = "fixture",
        priority: int | None = None,
        rule_url: str | None = None,
        readme_url: str | None = None,
        entry_key: str | None = None,
    ) -> dict[str, object]:
        if priority is None:
            priority = 100 if source == "fixture" else 200
        if rule_url is None:
            rule_url = (
                self.RULE_URL_PRIMARY
                if source == "fixture"
                else self.RULE_URL_SECONDARY
            )
        if readme_url is None:
            readme_url = (
                self.README_URL_PRIMARY
                if source == "fixture"
                else self.README_URL_SECONDARY
            )
        if entry_key is None:
            entry_key = f"{target}-{source}-{status}"
        target_dir = (
            self.TARGET_CLASH_DIR
            if target == self.TARGET_CLASH
            else self.TARGET_EGERN_DIR
            if target == self.TARGET_EGERN
            else target.capitalize()
        )
        return {
            "target": target,
            "target_dir": target_dir,
            "service": "OpenAI",
            "publish_mode": publish_mode,
            "selected_family": selected_family or ("native" if not is_converted else "clash"),
            "selected_native_target": selected_native_target
            or (self.TARGET_CLASH if is_converted else target),
            "source": source,
            "priority": priority,
            "rule_url": rule_url,
            "readme_url": readme_url,
            "status": status,
            "snapshot_path": snapshot_path,
            "entry_key": entry_key,
            "is_native": not is_converted,
            "is_converted": is_converted,
            "conversion_path": conversion_path
            or ("Clash -> Egern" if is_converted and target == self.TARGET_EGERN else None),
        }

    def _write_upstream_manifest(self, manifest: dict[str, list[dict[str, object]]]) -> None:
        manifest_path = self.root / "dist" / "manifests" / "upstream_docs.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_snapshot(self, relative_path: str, content: str) -> None:
        snapshot_file = self.root / relative_path
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(content, encoding="utf-8")

    def _write_snapshot_bytes(self, relative_path: str, content: bytes) -> None:
        snapshot_file = self.root / relative_path
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_bytes(content)

    def _read_target_readme(self, target_dir: str, service_name: str) -> str:
        return (self.root / "Rule" / target_dir / service_name / "README.md").read_text(
            encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
