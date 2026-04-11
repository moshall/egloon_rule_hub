from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.docs.render import write_markdown_docs
from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
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


class ServiceDocsRenderTests(unittest.TestCase):
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
                "dummy": TargetDef(name="dummy", enabled=True, file_ext="yaml"),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["dummy"],
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

    def test_service_index_links_to_service_detail_page(self) -> None:
        self._write_upstream_manifest({})

        write_markdown_docs(self.root, self.catalog)

        services_doc = (self.root / "docs" / "services.md").read_text(encoding="utf-8")
        self.assertIn("[OpenAI](services/OpenAI.md)", services_doc)

    def test_detail_page_contains_original_upstream_text_from_snapshot(self) -> None:
        self._write_snapshot(self.SNAPSHOT_PATH_PRIMARY, "# README\n\nOriginal upstream text\n")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_PRIMARY,
                    }
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertIn("Original upstream text", detail)

    def test_detail_page_contains_readme_and_rule_links(self) -> None:
        self._write_snapshot(self.SNAPSHOT_PATH_PRIMARY, "Primary README\n")
        self._write_snapshot(self.SNAPSHOT_PATH_SECONDARY, "Secondary README\n")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_PRIMARY,
                    },
                    {
                        "source": "mirror",
                        "rule_url": self.RULE_URL_SECONDARY,
                        "readme_url": self.README_URL_SECONDARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_SECONDARY,
                    },
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertIn(self.RULE_URL_PRIMARY, detail)
        self.assertIn(self.RULE_URL_SECONDARY, detail)
        self.assertIn(self.README_URL_PRIMARY, detail)
        self.assertIn(self.README_URL_SECONDARY, detail)

    def test_detail_page_shows_missing_and_fetch_error_states(self) -> None:
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "missing",
                        "snapshot_path": None,
                    },
                    {
                        "source": "mirror",
                        "rule_url": self.RULE_URL_SECONDARY,
                        "readme_url": self.README_URL_SECONDARY,
                        "status": "fetch_error",
                        "snapshot_path": None,
                    },
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertIn("upstream README missing", detail)
        self.assertIn("upstream README fetch_error", detail)

    def test_multi_entry_manifest_renders_multiple_upstream_blocks(self) -> None:
        self._write_snapshot(self.SNAPSHOT_PATH_PRIMARY, "Primary README\n")
        self._write_snapshot(self.SNAPSHOT_PATH_SECONDARY, "Secondary README\n")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_PRIMARY,
                    },
                    {
                        "source": "mirror",
                        "rule_url": self.RULE_URL_SECONDARY,
                        "readme_url": self.README_URL_SECONDARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_SECONDARY,
                    },
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertEqual(detail.count("### Upstream Entry"), 2)

    def test_traversal_style_snapshot_path_is_rejected(self) -> None:
        outside_file = self.root.parent / f"{self.root.name}-outside-README.md"
        outside_file.write_text("SHOULD NOT BE INLINED\n", encoding="utf-8")
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "ok",
                        "snapshot_path": f"../{outside_file.name}",
                    }
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertIn("upstream README missing snapshot", detail)
        self.assertNotIn("SHOULD NOT BE INLINED", detail)

    def test_snapshot_with_backticks_uses_safe_outer_code_fence(self) -> None:
        self._write_snapshot(
            self.SNAPSHOT_PATH_PRIMARY,
            "# README\n\n```bash\necho hi\n```\n",
        )
        self._write_upstream_manifest(
            {
                "OpenAI": [
                    {
                        "source": "fixture",
                        "rule_url": self.RULE_URL_PRIMARY,
                        "readme_url": self.README_URL_PRIMARY,
                        "status": "ok",
                        "snapshot_path": self.SNAPSHOT_PATH_PRIMARY,
                    }
                ]
            }
        )

        write_markdown_docs(self.root, self.catalog)

        detail = self._read_detail_page("OpenAI")
        self.assertIn("````text", detail)
        self.assertIn("```bash", detail)
        self.assertIn("\n````\n", detail)

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

    def _read_detail_page(self, service_name: str) -> str:
        return (self.root / "docs" / "services" / f"{service_name}.md").read_text(
            encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
