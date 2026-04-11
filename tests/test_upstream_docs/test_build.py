"""Tests for building upstream README snapshots and manifests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
    SourceDef,
    SourceRef,
    TargetDef,
)

from egloon_rule_hub.upstream_docs.build import build_upstream_docs


class BuildUpstreamDocsTests(unittest.TestCase):
    RULE_URL = "https://example.com/rule/Clash/OpenAI/OpenAI.yaml"
    RULE_URL_ALT = "https://example.com/rule/Loon/OpenAI/OpenAI.list"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.catalog = Catalog(
            root=self.root,
            sources={
                "fixture": SourceDef(name="fixture", kind="remote"),
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
                            url=self.RULE_URL,
                            format="clash_yaml",
                            priority=100,
                        ),
                        SourceRef(
                            source="fixture",
                            url=self.RULE_URL_ALT,
                            format="loon_list",
                            priority=90,
                        ),
                    ],
                ),
            },
            bundles={},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_happy_path_writes_snapshot_and_manifest(self) -> None:
        manifest = build_upstream_docs(self.catalog, fetcher=self._fake_fetcher())

        self.assertIn("OpenAI", manifest)
        entry = manifest["OpenAI"][0]
        self.assertEqual(entry["status"], "ok")

        snapshot_path = self.root / entry["snapshot_path"]
        self.assertTrue(snapshot_path.exists())
        self.assertTrue(snapshot_path.is_file())

    def test_manifest_snapshot_path_is_relative_to_root(self) -> None:
        manifest = build_upstream_docs(self.catalog, fetcher=self._fake_fetcher())
        entry = manifest["OpenAI"][0]
        snapshot_rel = Path(entry["snapshot_path"])

        self.assertFalse(snapshot_rel.is_absolute())
        self.assertTrue((self.root / snapshot_rel).exists())

    def test_entry_keys_differ_for_same_source_multiple_rules(self) -> None:
        manifest = build_upstream_docs(self.catalog, fetcher=self._fake_fetcher())
        entries = manifest["OpenAI"]

        self.assertGreater(len(entries), 1)
        self.assertNotEqual(entries[0]["entry_key"], entries[1]["entry_key"])
        first_snapshot = self.root / entries[0]["snapshot_path"]
        second_snapshot = self.root / entries[1]["snapshot_path"]
        self.assertNotEqual(first_snapshot, second_snapshot)

    def _fake_fetcher(self):
        def fetcher(url: str) -> bytes:
            return b"# README\n\nOriginal upstream text\n"

        return fetcher


if __name__ == "__main__":
    unittest.main()
