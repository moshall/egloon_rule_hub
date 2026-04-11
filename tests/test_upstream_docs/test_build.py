"""Tests for building upstream README snapshots and manifests."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
    SourceDef,
    SourceRef,
    TargetDef,
)

from egloon_rule_hub.upstream_docs.build import build_upstream_docs


def _slugify_path(path: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")
    return slug or "root"


def _expected_entry_key(priority: int, source: str, rule_url: str, entry_index: int) -> str:
    parsed = urlparse(rule_url)
    slug = _slugify_path(parsed.path or "/")
    digest = hashlib.sha1(rule_url.encode("utf-8")).hexdigest()[:8]
    return f"{priority}-{source}-{slug}-{digest}-{entry_index}"


class BuildUpstreamDocsTests(unittest.TestCase):
    RULE_URL = "https://example.com/rule/Clash/OpenAI/OpenAI.yaml"
    RULE_URL_ALT = "https://mirror.example.org/rule/Clash/OpenAI/OpenAI.yaml"

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
                            priority=100,
                        ),
                        SourceRef(
                            source="fixture",
                            url=self.RULE_URL,
                            format="some_other",
                            priority=100,
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
        self.assertEqual(snapshot_path.read_bytes(), b"# README\n\nOriginal upstream text\n")

        manifest_file = self.root / "dist" / "manifests" / "upstream_docs.json"
        self.assertTrue(manifest_file.exists())

        file_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(file_manifest, manifest)

        self.assertEqual(entry["readme_url"], "https://example.com/rule/Clash/OpenAI/README.md")
        self.assertEqual(entry["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL, 0))

    def test_manifest_snapshot_path_is_relative_to_root(self) -> None:
        manifest = build_upstream_docs(self.catalog, fetcher=self._fake_fetcher())
        entry = manifest["OpenAI"][0]
        snapshot_rel = Path(entry["snapshot_path"])

        self.assertFalse(snapshot_rel.is_absolute())
        self.assertTrue((self.root / snapshot_rel).exists())

    def test_entry_keys_differ_for_same_source_multiple_rules(self) -> None:
        manifest = build_upstream_docs(self.catalog, fetcher=self._fake_fetcher())
        entries = manifest["OpenAI"]

        self.assertGreater(len(entries), 2)
        self.assertEqual(entries[0]["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL, 0))
        self.assertEqual(entries[1]["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL_ALT, 1))
        self.assertEqual(entries[2]["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL, 2))
        self.assertNotEqual(entries[0]["entry_key"], entries[2]["entry_key"], "same URL should still get unique key per entry")

    def _fake_fetcher(self):
        def fetcher(url: str) -> bytes:
            return b"# README\n\nOriginal upstream text\n"

        return fetcher


if __name__ == "__main__":
    unittest.main()
