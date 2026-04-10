from __future__ import annotations

import yaml

from egloon_rule_hub.model.rules import Rule

EGERN_TYPE_MAP = {
    "domain_set": "DOMAIN",
    "domain_suffix_set": "DOMAIN-SUFFIX",
    "domain_keyword_set": "DOMAIN-KEYWORD",
    "domain_regex_set": "DOMAIN-REGEX",
    "ip_cidr_set": "IP-CIDR",
    "ip_cidr6_set": "IP-CIDR6",
    "asn_set": "IP-ASN",
}


def parse_egern_rule_set(content: str) -> list[Rule]:
    data = yaml.safe_load(content) or {}
    rules: list[Rule] = []
    for key, rule_type in EGERN_TYPE_MAP.items():
        for value in data.get(key, []) or []:
            rules.append(Rule(rule_type, str(value)))
    for value in data.get("geoip", []) or []:
        rules.append(Rule("GEOIP", str(value)))
    return rules

