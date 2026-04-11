"""Tests for the CLI bootstrap path."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import mock, TestCase

from egloon_rule_hub import cli


class BootstrapCLITest(TestCase):
    def test_bootstrap_calls_upstream_docs(self) -> None:
        root = Path(tempfile.mkdtemp())
        catalog = mock.Mock(root=root)

        with mock.patch("egloon_rule_hub.cli._run_validate", return_value=catalog), \
            mock.patch("egloon_rule_hub.cli.build_all_service_rules", return_value="rules"), \
            mock.patch("egloon_rule_hub.cli.render_rule_artifacts"), \
            mock.patch("egloon_rule_hub.cli._render_manifests"), \
            mock.patch("egloon_rule_hub.cli.write_markdown_docs"), \
            mock.patch("egloon_rule_hub.cli.build_upstream_docs") as build_upstream_docs:
            status = cli.main(["--root", str(root), "bootstrap"])

        self.assertEqual(status, 0)
        build_upstream_docs.assert_called_once_with(catalog)
