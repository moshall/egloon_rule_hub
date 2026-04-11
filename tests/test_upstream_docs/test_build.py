"""Tests for building upstream README snapshots and manifests."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from egloon_rule_hub.build import build_all_target_artifacts
from egloon_rule_hub.model.catalog import (
    Catalog,
    ServiceDef,
    ServiceTargetDef,
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
    RULE_URL_ALT = "https://mirror.example.org/rule/Loon/OpenAI/OpenAI.list"

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.catalog = Catalog(
            root=self.root,
            sources={
                "fixture": SourceDef(name="fixture", kind="remote"),
            },
            targets={
                "clash": TargetDef(name="clash", enabled=True, file_ext="yaml"),
                "loon": TargetDef(name="loon", enabled=True, file_ext="list"),
                "egern": TargetDef(name="egern", enabled=True, file_ext="yaml"),
            },
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["clash", "loon", "egern"],
                    target_sources={
                        "clash": ServiceTargetDef(
                            name="clash",
                            families={
                                "native": [
                                    SourceRef(
                                        source="fixture",
                                        url=self.RULE_URL,
                                        format="clash_yaml",
                                        priority=100,
                                    )
                                ],
                                "shadowrocket": [],
                                "clash": [],
                            },
                        ),
                        "loon": ServiceTargetDef(
                            name="loon",
                            families={
                                "native": [
                                    SourceRef(
                                        source="fixture",
                                        url=self.RULE_URL_ALT,
                                        format="loon_list",
                                        priority=100,
                                    )
                                ],
                                "shadowrocket": [],
                                "clash": [],
                            },
                        ),
                        "egern": ServiceTargetDef(
                            name="egern",
                            families={
                                "native": [],
                                "shadowrocket": [],
                                "clash": [
                                    SourceRef(
                                        source="fixture",
                                        url=self.RULE_URL,
                                        format="clash_yaml",
                                        priority=100,
                                    ),
                                    SourceRef(
                                        source="fixture",
                                        url=self.RULE_URL,
                                        format="clash_yaml",
                                        priority=100,
                                    ),
                                ],
                            },
                        ),
                    },
                ),
            },
            bundles={},
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_happy_path_writes_snapshot_and_manifest(self) -> None:
        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        manifest = build_upstream_docs(self.catalog, artifacts, fetcher=self._fake_fetcher())

        self.assertIn("OpenAI", manifest)
        entries = manifest["OpenAI"]
        clash_entry = next(entry for entry in entries if entry["target"] == "clash")
        self.assertEqual(clash_entry["status"], "ok")
        self.assertEqual(clash_entry["target_dir"], "Clash")
        self.assertFalse(clash_entry["is_converted"])
        self.assertTrue(clash_entry["is_native"])
        self.assertEqual(clash_entry["selected_family"], "native")
        self.assertEqual(clash_entry["selected_native_target"], "clash")
        self.assertIsNone(clash_entry["conversion_path"])
        self.assertEqual(clash_entry["service"], "OpenAI")
        self.assertEqual(clash_entry["readme_url"], "https://example.com/rule/Clash/OpenAI/README.md")
        self.assertEqual(
            clash_entry["entry_key"],
            _expected_entry_key(100, "fixture", self.RULE_URL, 0),
        )

        snapshot_path = self.root / clash_entry["snapshot_path"]
        self.assertTrue(snapshot_path.exists())
        self.assertTrue(snapshot_path.is_file())
        self.assertEqual(snapshot_path.read_bytes(), b"# README\n\nOriginal upstream text\n")

        manifest_file = self.root / "dist" / "manifests" / "upstream_docs.json"
        self.assertTrue(manifest_file.exists())

        file_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertEqual(file_manifest, manifest)

        converted_entry = next(
            entry for entry in entries if entry["target"] == "egern" and entry["rule_url"] == self.RULE_URL
        )
        self.assertEqual(converted_entry["target_dir"], "Egern")
        self.assertTrue(converted_entry["is_converted"])
        self.assertFalse(converted_entry["is_native"])
        self.assertEqual(converted_entry["selected_family"], "clash")
        self.assertEqual(converted_entry["selected_native_target"], "clash")
        self.assertEqual(converted_entry["conversion_path"], "Clash -> Egern")
        self.assertEqual(converted_entry["service"], "OpenAI")

    def test_manifest_snapshot_path_is_relative_to_root(self) -> None:
        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        manifest = build_upstream_docs(self.catalog, artifacts, fetcher=self._fake_fetcher())
        entry = next(entry for entry in manifest["OpenAI"] if entry.get("snapshot_path"))
        snapshot_rel = Path(entry["snapshot_path"])

        self.assertFalse(snapshot_rel.is_absolute())
        self.assertTrue((self.root / snapshot_rel).exists())

    def test_entry_keys_differ_for_same_source_multiple_rules(self) -> None:
        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        manifest = build_upstream_docs(self.catalog, artifacts, fetcher=self._fake_fetcher())
        entries = manifest["OpenAI"]

        self.assertGreater(len(entries), 2)
        clash_entry = next(
            entry for entry in entries if entry["target"] == "clash" and entry["rule_url"] == self.RULE_URL
        )
        loon_entry = next(
            entry for entry in entries if entry["target"] == "loon" and entry["rule_url"] == self.RULE_URL_ALT
        )
        converted_entry = next(
            entry for entry in entries
            if entry["target"] == "egern" and entry["entry_key"] == _expected_entry_key(100, "fixture", self.RULE_URL, 2)
        )

        self.assertEqual(clash_entry["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL, 0))
        self.assertEqual(loon_entry["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL_ALT, 1))
        self.assertEqual(converted_entry["entry_key"], _expected_entry_key(100, "fixture", self.RULE_URL, 2))
        self.assertNotEqual(
            clash_entry["entry_key"],
            converted_entry["entry_key"],
            "same URL should still get unique key per entry",
        )

    def test_rebuild_prunes_stale_snapshot_files(self) -> None:
        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        first_manifest = build_upstream_docs(self.catalog, artifacts, fetcher=self._fake_fetcher())

        stale_entry = next(
            entry
            for entry in first_manifest["OpenAI"]
            if entry["target"] == "loon"
        )
        stale_snapshot = self.root / stale_entry["snapshot_path"]
        stale_dir = stale_snapshot.parent
        self.assertTrue(stale_snapshot.exists())

        self.catalog.services["OpenAI"].target_sources["loon"].families["native"] = []

        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        build_upstream_docs(self.catalog, artifacts, fetcher=self._fake_fetcher())

        self.assertFalse(stale_snapshot.exists())
        self.assertFalse(stale_dir.exists())

    def test_duplicate_upstream_readmes_fetch_once_and_reuse_snapshot(self) -> None:
        artifacts = build_all_target_artifacts(self.catalog, fetcher=self._fake_source_fetcher())
        calls: list[str] = []

        def fetcher(url: str) -> bytes:
            calls.append(url)
            return b"# README\n\nOriginal upstream text\n"

        manifest = build_upstream_docs(self.catalog, artifacts, fetcher=fetcher)
        entries = manifest["OpenAI"]
        clash_entry = next(entry for entry in entries if entry["target"] == "clash")
        egern_entries = [entry for entry in entries if entry["target"] == "egern"]

        self.assertEqual(
            calls,
            [
                "https://example.com/rule/Clash/OpenAI/README.md",
                "https://mirror.example.org/rule/Loon/OpenAI/README.md",
            ],
        )
        self.assertEqual(clash_entry["readme_url"], "https://example.com/rule/Clash/OpenAI/README.md")
        self.assertEqual(
            {entry["readme_url"] for entry in egern_entries},
            {"https://example.com/rule/Clash/OpenAI/README.md"},
        )
        self.assertEqual(
            {entry["snapshot_path"] for entry in egern_entries + [clash_entry]},
            {clash_entry["snapshot_path"]},
        )

    def _fake_fetcher(self):
        def fetcher(url: str) -> bytes:
            return b"# README\n\nOriginal upstream text\n"

        return fetcher

    def _fake_source_fetcher(self):
        def fetcher(url: str) -> str:
            if url == self.RULE_URL:
                return "payload:\n  - DOMAIN,openai.com\n"
            if url == self.RULE_URL_ALT:
                return "# > OpenAI\nDOMAIN-SUFFIX,chatgpt.com\n"
            return "payload:\n  - DOMAIN,other.example\n"

        return fetcher


if __name__ == "__main__":
    unittest.main()
