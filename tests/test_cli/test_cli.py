"""Tests for the CLI bootstrap path."""

from __future__ import annotations

import os
import tempfile
from contextlib import ExitStack
from pathlib import Path
from unittest import mock, TestCase

from egloon_rule_hub import cli


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
