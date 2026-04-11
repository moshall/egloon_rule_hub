from __future__ import annotations

from pathlib import Path

from .manual import TxtServiceSnapshot, discover_txt_services, parse_txt_service_text
from egloon_rule_hub.txt_sources.feishu import refresh_feishu_txt


def refresh_txt_sources(root: Path) -> list[Path]:
    return [refresh_feishu_txt(root)]
