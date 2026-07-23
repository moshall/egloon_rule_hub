from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from egloon_rule_hub.txt_sources.feishu import (
    extract_feishu_update_time,
    refresh_feishu_txt,
)


class FeishuSourceTests(unittest.TestCase):
    def test_extracts_update_time_from_article_state(self) -> None:
        self.assertEqual(
            extract_feishu_update_time("updateTime: 1772767058,createTime: 1"),
            1772767058,
        )
        self.assertEqual(
            extract_feishu_update_time(r'\"updateTime\":1772767058000'),
            1772767058,
        )

    def test_unchanged_update_time_does_not_rewrite_snapshot(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_path = root / "Source" / "TXT" / "Feishu.txt"
            output_path.parent.mkdir(parents=True)
            original = (
                "# @upstream-update-time: 1772767058\n"
                "DOMAIN-SUFFIX,feishu.cn\n"
            )
            output_path.write_text(original, encoding="utf-8")

            refreshed = refresh_feishu_txt(
                root,
                fetcher=lambda _: "updateTime: 1772767058",
            )

            self.assertEqual(refreshed, output_path)
            self.assertEqual(output_path.read_text(encoding="utf-8"), original)

    def test_changed_update_time_writes_mainland_snapshot(self) -> None:
        article = (
            "updateTime: 1772767058\n"
            "域名:\n"
            "*.feishu.cn\n"
            "IP 白名单\n"
            "192.0.2.0/24 中国大陆\n"
            "198.51.100.0/24 新加坡\n"
        )
        with TemporaryDirectory() as temp_dir:
            output_path = refresh_feishu_txt(
                Path(temp_dir),
                fetcher=lambda _: article,
            )
            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("# @upstream-update-time: 1772767058", rendered)
        self.assertIn("# @upstream-updated-at: 2026-03-06T11:17:38+08:00", rendered)
        self.assertIn("# @upstream-region: 中国大陆", rendered)
        self.assertIn("DOMAIN-SUFFIX,feishu.cn", rendered)
        self.assertIn("IP-CIDR,192.0.2.0/24", rendered)
        self.assertNotIn("198.51.100.0/24", rendered)


if __name__ == "__main__":
    unittest.main()
