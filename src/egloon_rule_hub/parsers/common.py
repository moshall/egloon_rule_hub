from __future__ import annotations

import ipaddress
import re

from egloon_rule_hub.model.rules import Rule

_HOST_LABEL_PATTERN = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$",
    re.IGNORECASE,
)


def _looks_like_hostname(value: str, min_labels: int = 2) -> bool:
    parts = value.split(".")
    if len(parts) < min_labels:
        return False
    if all(part.isdigit() for part in parts):
        return False
    return all(_HOST_LABEL_PATTERN.fullmatch(part) for part in parts)


def parse_standard_or_raw_rule(raw_value: str) -> Rule:
    candidate = raw_value.strip().strip("'\"")
    if not candidate:
        raise ValueError("Empty rule entry is not supported")

    if "," in candidate:
        rule_type, value = candidate.split(",", 1)
        return Rule(rule_type.strip().upper(), value.strip())

    try:
        network = ipaddress.ip_network(candidate, strict=False)
    except ValueError:
        network = None
    if network is not None:
        rule_type = "IP-CIDR6" if network.version == 6 else "IP-CIDR"
        return Rule(rule_type, candidate)

    if candidate.isdigit():
        return Rule("IP-ASN", candidate)

    if candidate.startswith("+."):
        suffix = candidate[2:].strip()
        if _looks_like_hostname(suffix, min_labels=1):
            return Rule("DOMAIN-SUFFIX", suffix)
    if candidate.startswith("."):
        suffix = candidate.lstrip(".").strip()
        if _looks_like_hostname(suffix, min_labels=1):
            return Rule("DOMAIN-SUFFIX", suffix)
    if _looks_like_hostname(candidate):
        return Rule("DOMAIN", candidate)

    raise ValueError(f"Unsupported raw rule entry: {raw_value!r}")
