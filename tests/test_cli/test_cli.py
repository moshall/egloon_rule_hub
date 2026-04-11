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
from egloon_rule_hub.model.publish import SelectedSourceEntry, TargetArtifact
from egloon_rule_hub.model.rules import Rule


def _write_minimal_catalog(root: Path) -> None:
    catalog_dir = root / "catalog"
    catalog_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir = root / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    clash_rule = fixture_dir / "OpenAI.yaml"
    clash_rule.write_text(
        "payload:\n"
        "  - DOMAIN,openai.com\n",
        encoding="utf-8",
    )
    (catalog_dir / "sources.yaml").write_text(
        """sources:\n  sample:\n    kind: remote\n    repo: https://example.com\n""",
        encoding="utf-8",
    )
    (catalog_dir / "targets.yaml").write_text(
        """targets:\n  clash:\n    enabled: true\n    file_ext: yaml\n  egern:\n    enabled: true\n    file_ext: yaml\n""",
        encoding="utf-8",
    )
    (catalog_dir / "services.yaml").write_text(
        (
            "defaults:\n"
            "  fallback_order: [native, shadowrocket, clash]\n"
            "services:\n"
            "  OpenAI:\n"
            "    enabled: true\n"
            "    outputs: [clash, egern]\n"
            "    target_sources:\n"
            "      clash:\n"
            "        native:\n"
            f"          - source: sample\n            url: {clash_rule.as_uri()}\n"
            "            format: clash_yaml\n"
            "            priority: 100\n"
            "      egern:\n"
            "        native: []\n"
            "        shadowrocket: []\n"
            "        clash:\n"
            f"          - source: sample\n            url: {clash_rule.as_uri()}\n"
            "            format: clash_yaml\n"
            "            priority: 100\n"
        ),
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
                        mock.patch(
                            "egloon_rule_hub.cli.build_all_target_artifacts",
                            return_value="artifacts",
                        )
                    )
                    stack.enter_context(mock.patch("egloon_rule_hub.cli.render_target_artifacts"))
                    stack.enter_context(mock.patch("egloon_rule_hub.cli._render_manifests"))
                    write_markdown_docs = stack.enter_context(
                        mock.patch("egloon_rule_hub.cli.write_markdown_docs")
                    )
                    build_upstream_docs = stack.enter_context(
                        mock.patch("egloon_rule_hub.cli.build_upstream_docs")
                    )
                    status = cli.main(["--root", ".", "bootstrap"])
            finally:
                os.chdir(previous_cwd)

        self.assertEqual(status, 0)
        build_upstream_docs.assert_called_once_with(catalog, "artifacts")
        write_markdown_docs.assert_called_once_with(root, catalog, "artifacts")

    def test_render_docs_does_not_rebuild_target_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = mock.Mock(root=root)

            with ExitStack() as stack:
                stack.enter_context(
                    mock.patch("egloon_rule_hub.cli._run_validate", return_value=catalog)
                )
                build_all_target_artifacts = stack.enter_context(
                    mock.patch("egloon_rule_hub.cli.build_all_target_artifacts")
                )
                write_markdown_docs = stack.enter_context(
                    mock.patch("egloon_rule_hub.cli.write_markdown_docs")
                )

                status = cli.main(["--root", str(root), "render-docs"])

        self.assertEqual(status, 0)
        build_all_target_artifacts.assert_not_called()
        write_markdown_docs.assert_called_once_with(root, catalog)

    def test_bootstrap_generates_rule_and_readme_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_minimal_catalog(root)
            generated_artifacts = {
                "OpenAI": {
                    "clash": TargetArtifact(
                        service="OpenAI",
                        target="clash",
                        selected_family="native",
                        selected_native_target="clash",
                        publish_mode=None,
                        is_native=True,
                        is_converted=False,
                        conversion_path=None,
                        rules=[Rule("DOMAIN", "openai.com")],
                        selected_entries=[
                            SelectedSourceEntry(
                                source_name="sample",
                                family="native",
                                format="clash_yaml",
                                url="https://example.com/rule/Clash/OpenAI/OpenAI.yaml",
                                priority=100,
                                raw_text="payload:\n  - DOMAIN,openai.com\n",
                            )
                        ],
                    ),
                    "egern": TargetArtifact(
                        service="OpenAI",
                        target="egern",
                        selected_family="clash",
                        selected_native_target="clash",
                        publish_mode=None,
                        is_native=False,
                        is_converted=True,
                        conversion_path="Clash -> Egern",
                        rules=[Rule("DOMAIN", "openai.com")],
                        selected_entries=[
                            SelectedSourceEntry(
                                source_name="sample",
                                family="clash",
                                format="clash_yaml",
                                url="https://example.com/rule/Clash/OpenAI/OpenAI.yaml",
                                priority=100,
                                raw_text="payload:\n  - DOMAIN,openai.com\n",
                            )
                        ],
                    ),
                }
            }

            def fake_build_all_target_artifacts(
                catalog: Catalog,
            ) -> dict[str, dict[str, TargetArtifact]]:
                self.assertEqual(root, catalog.root)
                return generated_artifacts

            def fake_build_upstream_docs(
                catalog: Catalog,
                artifacts: dict[str, dict[str, TargetArtifact]],
            ) -> dict[str, list[dict[str, object]]]:
                self.assertEqual(root, catalog.root)
                self.assertEqual(artifacts, generated_artifacts)
                return _write_upstream_manifest(root)

            with ExitStack() as stack:
                stack.enter_context(
                    mock.patch(
                        "egloon_rule_hub.cli.build_all_target_artifacts",
                        side_effect=fake_build_all_target_artifacts,
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

    def test_render_manifests_uses_distinct_target_source_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _write_minimal_catalog(root)
            catalog = cli.load_catalog(root)

            cli._render_manifests(root, catalog)

            services_manifest = json.loads(
                (root / "dist" / "manifests" / "services.json").read_text(encoding="utf-8")
            )

        self.assertEqual(services_manifest["OpenAI"]["source_count"], 1)


class WorkflowConfigTests(TestCase):
    def test_sync_workflow_stages_rule_directory(self) -> None:
        workflow_path = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "sync-rules.yml"
        )
        workflow_text = workflow_path.read_text(encoding="utf-8")
        self.assertIn("git add Rule docs dist Source/TXT", workflow_text)

    def test_sync_workflow_refreshes_txt_sources(self) -> None:
        workflow_path = (
            Path(__file__).resolve().parents[2] / ".github" / "workflows" / "sync-rules.yml"
        )
        workflow_text = workflow_path.read_text(encoding="utf-8")
        self.assertIn("python -m egloon_rule_hub refresh-txt-sources", workflow_text)


class RefreshTxtSourcesCLITests(TestCase):
    def test_refresh_txt_sources_calls_refresh_function(self) -> None:
        with ExitStack() as stack:
            refresh_txt_sources = stack.enter_context(
                mock.patch("egloon_rule_hub.cli.refresh_txt_sources")
            )
            status = cli.main(["--root", ".", "refresh-txt-sources"])

        self.assertEqual(status, 0)
        refresh_txt_sources.assert_called_once_with(Path(".").resolve())
