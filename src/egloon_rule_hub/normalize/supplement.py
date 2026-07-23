from __future__ import annotations

from ipaddress import ip_network

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.normalize.dedupe import dedupe_rules


def _domain_is_covered(rule: Rule, existing: list[Rule]) -> bool:
    value = rule.value.lower().lstrip(".")
    for candidate in existing:
        candidate_value = candidate.value.lower().lstrip(".")
        if candidate.type == "DOMAIN-KEYWORD" and candidate_value in value:
            return True
        if candidate.type != "DOMAIN-SUFFIX":
            continue
        if value == candidate_value or value.endswith(f".{candidate_value}"):
            return True
    return False


def _network_is_covered(rule: Rule, existing: list[Rule]) -> bool:
    try:
        network = ip_network(rule.value, strict=False)
    except ValueError:
        return False
    for candidate in existing:
        if candidate.type not in {"IP-CIDR", "IP-CIDR6"}:
            continue
        try:
            candidate_network = ip_network(candidate.value, strict=False)
        except ValueError:
            continue
        if (
            candidate_network.version == network.version
            and network.subnet_of(candidate_network)
        ):
            return True
    return False


def is_rule_covered(rule: Rule, existing: list[Rule]) -> bool:
    if rule in existing:
        return True
    if rule.type in {"DOMAIN", "DOMAIN-SUFFIX"}:
        return _domain_is_covered(rule, existing)
    if rule.type in {"IP-CIDR", "IP-CIDR6"}:
        return _network_is_covered(rule, existing)
    return False


def append_missing_rules(
    primary_rules: list[Rule], supplement_rules: list[Rule]
) -> list[Rule]:
    merged = dedupe_rules(primary_rules)
    for rule in dedupe_rules(supplement_rules):
        if is_rule_covered(rule, merged):
            continue
        merged.append(rule)
    return merged
