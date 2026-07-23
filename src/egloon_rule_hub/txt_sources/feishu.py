from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
from urllib.request import Request, urlopen


FEISHU_ARTICLE_URL = (
    "https://www.feishu.cn/hc/zh-CN/articles/360044683233-"
    "%E9%85%8D%E7%BD%AE%E4%BC%81%E4%B8%9A%E5%86%85%E7%BD%91"
    "%E9%98%B2%E7%81%AB%E5%A2%99%E5%9F%9F%E5%90%8D%E5%92%8C-ip-"
    "%E7%99%BD%E5%90%8D%E5%8D%95"
)

_WILDCARD_DOMAIN_PATTERN = re.compile(r"\*\.([A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,})")
_CIDR_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b")
_UPDATE_TIME_PATTERNS = (
    re.compile(r"\bupdateTime\s*:\s*(\d{10,13})\b"),
    re.compile(r'(?:\\?")updateTime(?:\\?")\s*:\s*(\d{10,13})\b'),
)
_STORED_UPDATE_TIME_PATTERN = re.compile(
    r"^#\s*@upstream-update-time:\s*(\d+)\s*$",
    re.MULTILINE,
)
_CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


def _dedupe_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def fetch_feishu_article(url: str = FEISHU_ARTICLE_URL) -> str:
    request = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; egloon-rule-hub/0.1)"},
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


def extract_feishu_update_time(html: str) -> int:
    for pattern in _UPDATE_TIME_PATTERNS:
        if match := pattern.search(html):
            raw_value = int(match.group(1))
            return raw_value // 1000 if raw_value >= 10**12 else raw_value
    raise ValueError("Failed to extract Feishu upstream update time")


def _stored_feishu_update_time(text: str) -> int | None:
    if match := _STORED_UPDATE_TIME_PATTERN.search(text):
        return int(match.group(1))
    return None


def _format_feishu_update_time(update_time: int) -> str:
    return datetime.fromtimestamp(
        update_time,
        tz=timezone.utc,
    ).astimezone(_CHINA_STANDARD_TIME).isoformat(timespec="seconds")


def _domain_section(html: str) -> str:
    start = html.find("域名:\\n")
    if start < 0:
        start = html.find("域名:\n")
    if start < 0:
        start = 0
    end_candidates = [
        index
        for marker in ("中国大陆", "IP白名单", "IP 白名单")
        if (index := html.find(marker, start)) >= 0
    ]
    end = min(end_candidates) if end_candidates else len(html)
    return html[start:end]


def extract_feishu_domains(html: str) -> list[str]:
    section = _domain_section(html)
    matches = (
        match.group(1).strip().rstrip(".").lower()
        for match in _WILDCARD_DOMAIN_PATTERN.finditer(section)
    )
    return _dedupe_preserving_order(matches)


def extract_mainland_cidrs(html: str) -> list[str]:
    matches = list(_CIDR_PATTERN.finditer(html))
    mainland_cidrs: list[str] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(html)
        window = html[match.end() : next_start]
        if "中国大陆" not in window:
            continue
        mainland_cidrs.append(match.group(0))
    return _dedupe_preserving_order(mainland_cidrs)


def render_feishu_txt(
    domains: list[str],
    mainland_cidrs: list[str],
    update_time: int,
) -> str:
    lines = [
        "# 数据来源: Feishu 官方帮助中心",
        f"# 原文链接: {FEISHU_ARTICLE_URL}",
        f"# @upstream-update-time: {update_time}",
        f"# @upstream-updated-at: {_format_feishu_update_time(update_time)}",
        "# @upstream-region: 中国大陆",
        "# 规则名称: Feishu-域名",
    ]
    lines.extend(f"DOMAIN-SUFFIX,{domain}" for domain in domains)
    lines.append("# 规则名称: Feishu-中国大陆IP")
    lines.extend(f"IP-CIDR,{cidr}" for cidr in mainland_cidrs)
    return "\n".join(lines) + "\n"


def refresh_feishu_txt(
    root: Path,
    fetcher: Callable[[str], str] | None = None,
) -> Path:
    fetcher = fetcher or fetch_feishu_article
    html = fetcher(FEISHU_ARTICLE_URL)
    update_time = extract_feishu_update_time(html)
    output_path = root / "Source" / "TXT" / "Feishu.txt"
    if output_path.exists():
        current_text = output_path.read_text(encoding="utf-8")
        if _stored_feishu_update_time(current_text) == update_time:
            return output_path

    domains = extract_feishu_domains(html)
    mainland_cidrs = extract_mainland_cidrs(html)
    if not domains or not mainland_cidrs:
        raise ValueError("Failed to extract Feishu domains or mainland CIDRs")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_feishu_txt(
            domains=domains,
            mainland_cidrs=mainland_cidrs,
            update_time=update_time,
        ),
        encoding="utf-8",
    )
    return output_path
