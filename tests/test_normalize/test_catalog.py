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
        self.assertEqual(readme.count("### Upstream Entry"), 3)
        self.assertIn("upstream README missing", readme)
        self.assertIn("upstream README fetch_error", readme)
        self.assertIn("Converted upstream text", readme)

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
            "source": source,
            "priority": priority,
            "rule_url": rule_url,
            "readme_url": readme_url,
            "status": status,
            "snapshot_path": snapshot_path,
            "entry_key": entry_key,
            "is_converted": is_converted,
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
