from __future__ import annotations

SUPPORTED_RULE_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-REGEX",
    "IP-CIDR",
    "IP-CIDR6",
    "GEOIP",
    "IP-ASN",
}


def is_supported_rule_type(rule_type: str) -> bool:
    return rule_type.upper() in SUPPORTED_RULE_TYPES

