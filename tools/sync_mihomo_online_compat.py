"""Publish Mihomo providers converted from the original public Egern/SR feeds.

Does not read or publish user profiles, proxy subscriptions, or credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import time
import urllib.request

import yaml

BASE = Path(__file__).resolve().parents[1]
SOURCES = {
    "route_06": ("egern", "https://gist.githubusercontent.com/moshall/bdcaaca288bad5adfe5d2c9a926de873/raw/79f842b8eda7bec3b26a923790992c120b695f2d/picopi_inner_rule_set.yaml", False),
    "route_31": ("shadowrocket", "https://raw.githubusercontent.com/GMOogway/shadowrocket-rules/master/sr_direct_list.module", False),
    "route_32": ("egern", "https://raw.githubusercontent.com/Repcz/Tool/refs/heads/X/Egern/Rules/Lan.yaml", False),
    "dns_forward_0": ("egern", "https://raw.githubusercontent.com/Repcz/Tool/refs/heads/X/Egern/Rules/Lan.yaml", True),
    "dns_forward_1": ("egern", "https://raw.githubusercontent.com/Repcz/EgernRules/refs/heads/X/Rules/China/China_All.yaml", True),
    "dns_forward_4": ("egern", "https://raw.githubusercontent.com/Repcz/EgernRules/refs/heads/X/Rules/Global/Global_All.yaml", True),
}
FIELDS = {
    "domain_set": "DOMAIN", "domain_suffix_set": "DOMAIN-SUFFIX",
    "domain_keyword_set": "DOMAIN-KEYWORD", "domain_regex_set": "DOMAIN-REGEX",
    "domain_wildcard_set": "DOMAIN-WILDCARD", "geoip_set": "GEOIP",
    "asn_set": "IP-ASN", "ip_cidr_set": "IP-CIDR", "ip_cidr6_set": "IP-CIDR6",
}
SR_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN"}
STATIC = {
    "dns_forward_2": ["DOMAIN-WILDCARD,*.icloud.com"],
    "dns_forward_3": ["DOMAIN-WILDCARD,*.goog"],
}


def download(url: str) -> str:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "clash.meta"})
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read().decode("utf-8-sig")
        except (OSError, UnicodeError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def convert_egern(text: str, domains_only: bool) -> tuple[list[str], dict]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Egern feed must be a mapping")
    payload = []
    skipped = {}
    for field, values in data.items():
        if domains_only and not field.startswith("domain"):
            skipped[field] = len(values) if isinstance(values, list) else 1
            continue
        rule_type = FIELDS.get(field)
        if rule_type is None:
            if field == "no_resolve":
                continue
            raise ValueError(f"Unsupported Egern field: {field}")
        if not isinstance(values, list):
            raise ValueError(f"Expected list: {field}")
        for value in values:
            if not isinstance(value, (str, int)):
                raise ValueError(f"Invalid value in {field}")
            value = str(value)
            if field.startswith("ip_cidr"):
                rule_type = "IP-CIDR6" if ipaddress.ip_network(value, strict=False).version == 6 else "IP-CIDR"
            payload.append(f"{rule_type},{value}")
    return list(dict.fromkeys(payload)), skipped


def convert_shadowrocket(text: str) -> tuple[list[str], dict]:
    payload = []
    skipped = {}
    in_rules = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            in_rules = line.lower() == "[rule]"
            continue
        if not in_rules:
            continue
        parts = line.split(",")
        if parts[0] not in SR_TYPES:
            if parts[0] == "URL-REGEX":
                skipped[parts[0]] = skipped.get(parts[0], 0) + 1
                continue
            raise ValueError(f"Unexpected Shadowrocket rule: {parts[0]}")
        if len(parts) < 2 or not parts[1]:
            raise ValueError("Malformed Shadowrocket rule")
        payload.append(",".join(parts[:2]))
    return list(dict.fromkeys(payload)), skipped


def build(output: Path) -> dict:
    contents = {}
    metadata = {}
    cache = {}
    for name, (kind, url, domains_only) in SOURCES.items():
        if url not in cache:
            cache[url] = download(url)
        text = cache[url]
        payload, skipped = convert_shadowrocket(text) if kind == "shadowrocket" else convert_egern(text, domains_only)
        if not payload:
            raise ValueError(f"Empty converted feed: {name}")
        contents[name] = yaml.safe_dump({"payload": payload}, allow_unicode=True, sort_keys=False, width=160)
        metadata[name] = {"source": url, "source_format": kind, "domain_only": domains_only, "count": len(payload), "skipped": skipped, "sha256": hashlib.sha256(contents[name].encode()).hexdigest()}
    for name, payload in STATIC.items():
        contents[name] = yaml.safe_dump({"payload": payload}, allow_unicode=True, sort_keys=False)
        metadata[name] = {"source": "original domain condition", "count": len(payload), "sha256": hashlib.sha256(contents[name].encode()).hexdigest()}
    # No outputs change until every upstream has downloaded and converted.
    output.mkdir(parents=True, exist_ok=True)
    for name, text in contents.items():
        temp = output / f".{name}.tmp"
        temp.write_text(text, encoding="utf-8")
        temp.replace(output / f"{name}.yaml")
    manifest = output / "manifest.json"
    manifest.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE / "Rule/Clash/OnlineCompat")
    args = parser.parse_args()
    print(json.dumps({name: item["count"] for name, item in build(args.output).items()}, ensure_ascii=False))
