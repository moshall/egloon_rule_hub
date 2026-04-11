from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from egloon_rule_hub.txt_sources.feishu import (
    extract_feishu_domains,
    extract_mainland_cidrs,
    refresh_feishu_txt,
    render_feishu_txt,
)


SAMPLE_FEISHU_HTML = """
window._templateValue = {
  "content": "域名:\\n*.feishu.net\\n*.feishu.cn\\n*.larkoffice.com\\n"
};
111.48.147.0/24 foo 中国大陆 华中 湖北
52.81.23.0/24 foo 海外 ap-southeast-1
120.226.53.0/24 bar 中国大陆 华中 湖南
111.48.147.0/24 foo 中国大陆 华中 湖北
"""

NOISY_FEISHU_HTML = """
域名:
*.wrong.example
IP 白名单
window._templateValue = {
  "content": "域名:\\n*.feishu.net\\n*.feishu.cn\\n*.larkoffice.com\\n中国大陆"
};
"""


class FeishuTxtTests(TestCase):
    def test_extract_feishu_domains_preserves_order_and_dedupes(self) -> None:
        self.assertEqual(
            extract_feishu_domains(SAMPLE_FEISHU_HTML),
            ["feishu.net", "feishu.cn", "larkoffice.com"],
        )

    def test_extract_feishu_domains_prefers_article_payload_over_page_noise(self) -> None:
        self.assertEqual(
            extract_feishu_domains(NOISY_FEISHU_HTML),
            ["feishu.net", "feishu.cn", "larkoffice.com"],
        )

    def test_extract_mainland_cidrs_filters_non_mainland_rows(self) -> None:
        self.assertEqual(
            extract_mainland_cidrs(SAMPLE_FEISHU_HTML),
            ["111.48.147.0/24", "120.226.53.0/24"],
        )

    def test_render_feishu_txt_uses_manual_txt_style(self) -> None:
        rendered = render_feishu_txt(
            domains=["feishu.net", "larkoffice.com"],
            mainland_cidrs=["111.48.147.0/24"],
        )

        self.assertIn("# 规则名称: Feishu-域名", rendered)
        self.assertIn("DOMAIN-SUFFIX,feishu.net", rendered)
        self.assertIn("DOMAIN-SUFFIX,larkoffice.com", rendered)
        self.assertIn("# 规则名称: Feishu-中国大陆IP", rendered)
        self.assertIn("IP-CIDR,111.48.147.0/24", rendered)

    def test_refresh_feishu_txt_writes_source_txt_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            output_path = refresh_feishu_txt(
                root,
                fetcher=lambda url: SAMPLE_FEISHU_HTML,
            )

            self.assertEqual(output_path, root / "Source" / "TXT" / "Feishu.txt")
            self.assertTrue(output_path.exists())
            rendered = output_path.read_text(encoding="utf-8")

        self.assertIn("DOMAIN-SUFFIX,feishu.net", rendered)
        self.assertIn("DOMAIN-SUFFIX,feishu.cn", rendered)
        self.assertIn("IP-CIDR,120.226.53.0/24", rendered)
