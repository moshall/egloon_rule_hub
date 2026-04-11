"""Tests for the CLI bootstrap path."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest import mock, TestCase

from egloon_rule_hub import cli
from egloon_rule_hub.model.catalog import Catalog
from egloon_rule_hub.model.rules import Rule


def _write_minimal_catalog(root: Path) -> None:
    catalog_dir = root / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    (catalog_dir / "sources.yaml").write_text(
        """sources:\n  sample:\n    kind: remote\n    repo: https://example.com\n""",
        encoding="utf-8",
    )
    (catalog_dir / "targets.yaml").write_text(
        """targets:\n  clash:\n    enabled: true\n    file_ext: yaml\n  egern:\n    enabled: true\n    file_ext: yaml\n""",
        encoding="utf-8",
    )
    (catalog_dir / "services.yaml").write_text(
        """services:\n  OpenAI:\n    enabled: true\n    targets: [clash, egern]\n    sources:\n      - source: sample\n        url: https://example.com/rule/openai.yaml\n        format: clash_yaml\n        priority: 100\n""",
        encoding="utf-8",
    )
    (catalog_dir / "bundles.yaml").write_text(
        """bundles:\n  minimal:\n    enabled: true\n    targets: [clash, egern]\n    services: [OpenAI]\n""",
        encoding="utf-8",
    )


def _write_upstream_manifest(root: Path) -> dict[str, list[dict[str, object]]]:
    manifest = {
        "OpenAI": [
            {
                "target": "clash",
                "target_dir": "Clash",
                "service": "OpenAI",
                "source": "sample",
                "priority": 1,
                "rule_url": "https://example.com/rule/Clash/OpenAI.yaml",
                "readme_url": "https://example.com/README.md",
                "status": "ok",
                "snapshot_path": None,
                "entry_key": "clash-openai",
                "is_converted": False,
            },
            {
                "target": "egern",
                "target_dir": "Egern",
                "service": "OpenAI",
                "source": "sample",
                "priority": 1,
                "rule_url": "https://example.com/rule/Egern/OpenAI.yaml",
                "readme_url": "https://example.com/README.md",
                "status": "converted",
                "snapshot_path": None,
                "entry_key": "egern-openai",
                "is_converted": True,
            },
        ]
    }
    manifest_path = root / "dist" / "manifests" / "upstream_docs.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


class BootstrapCLITest(TestCase):
    def test_bootstrap_calls_upstream_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = mock.Mock(root=root)
            previous_cwd = Path.cwd()
            os.chdir(root)
            try:
                with ExitStack() as stack:
                    stack.enter_context(
                        mock.patch("egloon_rule_hub.cli._run_validate", return_value=catalog)
                    )
                    stack.enter_context(
                        mock.patch("egloon_rule_hub.cli.build_all_service_rules", return_value="rules")
                    )
                    stack.enter_context(mock.patch("egloon_rule_hub.cli.render_rule_artifacts"))
                    stack.enter_context(mock.patch("egloon_rule_hub.cli._render_manifests"))
                    stack.enter_context(mock.patch("egloon_rule_hub.cli.write_markdown_docs"))
                    build_upstream_docs = stack.enter_context(
                        mock.patch("egloon_rule_hub.cli.build_upstream_docs")
                    )
                    status = cli.main(["--root", ".", "bootstrap"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(status, 0)
        build_upstream_docs.assert_called_once_with(catalog)

    def test_bootstrap_generates_rule_and_readme_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_minimal_catalog(root)

            generated_rules = {
                "OpenAI": [Rule("DOMAIN-SUFFIX", "openai.com")]
            }

            def fake_build_all_service_rules(catalog: Catalog) -> dict[str, list[Rule]]:
                self.assertEqual(root, catalog.root)
                return generated_rules

            def fake_build_upstream_docs(
                catalog: Catalog
            ) -> dict[str, list[dict[str, object]]]:
                self.assertEqual(root, catalog.root)
                return _write_upstream_manifest(root)

            with ExitStack() as stack:
                stack.enter_context(
                    mock.patch(
                        "egloon_rule_hub.cli.build_all_service_rules",
                        side_effect=fake_build_all_service_rules,
                    )
                )
                stack.enter_context(
                    mock.patch(
                        "egloon_rule_hub.cli.build_upstream_docs",
                        side_effect=fake_build_upstream_docs,
                    )
                )
                status = cli.main(["--root", str(root), "bootstrap"])

            self.assertEqual(status, 0)

            expected_paths = [
                root / "Rule" / "Clash" / "OpenAI" / "OpenAI.yaml",
                root / "Rule" / "Clash" / "OpenAI" / "README.md",
                root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml",
                root / "Rule" / "Egern" / "OpenAI" / "README.md",
            ]
            for path in expected_paths:
                with self.subTest(path=path):
                    self.assertTrue(path.exists(), f"{path} is missing from bootstrap output")


class WorkflowConfigTests(TestCase):
    def test_sync_workflow_stages_rule_directory(self) -> None:
        workflow_path = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "sync-rules.yml"
        )
        workflow_text = workflow_path.read_text(encoding="utf-8")
        self.assertIn("git add Rule docs dist", workflow_text)
