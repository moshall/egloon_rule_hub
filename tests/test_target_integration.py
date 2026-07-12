from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.build import (
    TARGET_DISPLAY_NAMES,
    _render_target_output,
    _target_output_ext,
)
from egloon_rule_hub.cli import _render_manifests
from egloon_rule_hub.docs.render import _target_display_name
from egloon_rule_hub.model.catalog import load_catalog
from egloon_rule_hub.model.rules import Rule


class TargetIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.catalog = load_catalog(self.repo_root)

    def test_build_registers_new_renderers_extensions_and_display_names(self) -> None:
        rules = [Rule("DOMAIN-SUFFIX", "example.com")]
        try:
            surfboard = _render_target_output(
                "Example",
                "surfboard",
                self.catalog.targets["surfboard"],
                rules,
            )
            singbox = _render_target_output(
                "Example",
                "singbox",
                self.catalog.targets["singbox"],
                rules,
            )
        except ValueError as exc:
            self.fail(f"new target renderer is not registered: {exc}")

        self.assertEqual(surfboard, "DOMAIN-SUFFIX,example.com\n")
        self.assertEqual(json.loads(singbox)["version"], 1)
        self.assertEqual(
            _target_output_ext("surfboard", self.catalog.targets["surfboard"]),
            "list",
        )
        self.assertEqual(
            _target_output_ext("singbox", self.catalog.targets["singbox"]),
            "json",
        )
        self.assertEqual(TARGET_DISPLAY_NAMES["surfboard"], "Surfboard")
        self.assertEqual(TARGET_DISPLAY_NAMES["singbox"], "SingBox")
        self.assertEqual(_target_display_name("singbox"), "SingBox")

    def test_target_manifest_exposes_source_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _render_manifests(root, self.catalog)
            targets = json.loads(
                (root / "dist" / "manifests" / "targets.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(targets["surfboard"]["source_target"], "shadowrocket")
        self.assertEqual(targets["singbox"]["source_target"], "shadowrocket")


if __name__ == "__main__":
    unittest.main()
