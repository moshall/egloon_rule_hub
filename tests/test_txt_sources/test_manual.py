from __future__ import annotations

import tempfile
from pathlib import Path
from textwrap import dedent
import unittest
from unittest.mock import patch

from egloon_rule_hub.txt_sources import manual


class ManualTxtDiscoveryTests(unittest.TestCase):
    def test_discover_txt_services_and_relaxed_rules(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            txt_dir = root / "Source" / "TXT"
            txt_dir.mkdir(parents=True)
            (txt_dir / "ignore.me").write_text("# not a txt source", encoding="utf-8")
            (txt_dir / "Feishu.txt").write_text("# feishu placeholder\n", encoding="utf-8")
            (txt_dir / "IyfTv.txt").write_text(
                dedent(
                    """\
                    # just a comment
                    # @source_url: https://example.com/original
                    # @generated_by: unit-test
                    example.com
                    1.2.3.0/24
                    DOMAIN,api.example.com
                    DOMAIN-SUFFIX,cdn.example.com
                    DOMAIN-SUFFIX,cdn.example.com
                    """
                ),
                encoding="utf-8",
            )

            snapshots = manual.discover_txt_services(root)
            self.assertEqual({snap.service_name for snap in snapshots}, {"Feishu", "IyfTv"})

            iyftv = next(snap for snap in snapshots if snap.service_name == "IyfTv")
            self.assertEqual(
                iyftv.metadata,
                {"source_url": "https://example.com/original", "generated_by": "unit-test"},
            )

            rendered_rules = [rule.render() for rule in iyftv.rules]
            self.assertEqual(
                rendered_rules,
                [
                    "DOMAIN-SUFFIX,example.com",
                    "IP-CIDR,1.2.3.0/24",
                    "DOMAIN,api.example.com",
                    "DOMAIN-SUFFIX,cdn.example.com",
                ],
            )

            self.assertNotIn("ignore.me", {snap.service_name for snap in snapshots})

    def test_invalid_cidr_shorthand_is_ignored(self):
        metadata, rules = manual.parse_txt_service_text("999.999.999.999/99\n")
        self.assertEqual(metadata, {})
        self.assertEqual(rules, [])

    def test_bom_prefixed_lines_are_parsed(self):
        content = "\ufeff# @source_url: https://example.com\nexample.com\n"
        metadata, rules = manual.parse_txt_service_text(content)
        self.assertEqual(metadata, {"source_url": "https://example.com"})
        self.assertEqual([rule.render() for rule in rules], ["DOMAIN-SUFFIX,example.com"])

    def test_discover_handles_txt_directory_as_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            source_dir = root / "Source"
            source_dir.mkdir()
            (source_dir / "TXT").write_text("not a directory", encoding="utf-8")
            self.assertEqual(manual.discover_txt_services(root), [])

    def test_discover_continues_when_one_txt_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            txt_dir = root / "Source" / "TXT"
            txt_dir.mkdir(parents=True)
            (txt_dir / "Good.txt").write_text("DOMAIN-SUFFIX,good.example\n", encoding="utf-8")
            (txt_dir / "Bad.txt").write_text("DOMAIN-SUFFIX,bad.example\n", encoding="utf-8")

            failures: dict[str, str] = {}

            original_parse = manual.parse_txt_service_text

            def flaky_parser(text: str):
                if "bad.example" in text:
                    raise ValueError("bad txt payload")
                return original_parse(text)

            with patch("egloon_rule_hub.txt_sources.manual.parse_txt_service_text", side_effect=flaky_parser):
                snapshots = manual.discover_txt_services(root, failures=failures)

            self.assertEqual([snap.service_name for snap in snapshots], ["Good"])
            self.assertEqual(failures["Source/TXT/Bad.txt"], "bad txt payload")
