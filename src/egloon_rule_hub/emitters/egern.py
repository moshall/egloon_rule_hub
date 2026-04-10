from __future__ import annotations

import yaml

from egloon_rule_hub.model.rules import Rule

EGERN_BUCKETS = {
    "DOMAIN": "domain_set",
    "DOMAIN-SUFFIX": "domain_suffix_set",
    "DOMAIN-KEYWORD": "domain_keyword_set",
    "DOMAIN-REGEX": "domain_regex_set",
    "IP-CIDR": "ip_cidr_set",
    "IP-CIDR6": "ip_cidr6_set",
    "IP-ASN": "asn_set",
    "GEOIP": "geoip",
}


def _normalize_egern_value(rule: Rule) -> str:
    if rule.type in {"IP-CIDR", "IP-CIDR6"}:
        return rule.value.split(",", 1)[0].strip()
    return rule.value


def render_egern_rule_set(rules: list[Rule]) -> str:
    payload: dict[str, list[str]] = {bucket: [] for bucket in EGERN_BUCKETS.values()}
    seen: dict[str, set[str]] = {bucket: set() for bucket in EGERN_BUCKETS.values()}
    for rule in rules:
        bucket = EGERN_BUCKETS.get(rule.type)
        if bucket is None:
            continue
        normalized = _normalize_egern_value(rule)
        if normalized in seen[bucket]:
            continue
        seen[bucket].add(normalized)
        payload[bucket].append(normalized)
    payload = {key: value for key, value in payload.items() if value}
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
