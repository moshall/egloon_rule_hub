from __future__ import annotations

import json

from egloon_rule_hub.model.rules import Rule

SINGBOX_TYPE_ALIASES = {
    "HOST": "DOMAIN",
    "HOST-SUFFIX": "DOMAIN-SUFFIX",
    "HOST-KEYWORD": "DOMAIN-KEYWORD",
    "IP6-CIDR": "IP-CIDR6",
}

SINGBOX_RULE_FIELDS = {
    "DOMAIN": "domain",
    "DOMAIN-SUFFIX": "domain_suffix",
    "DOMAIN-KEYWORD": "domain_keyword",
    "DOMAIN-REGEX": "domain_regex",
    "IP-CIDR": "ip_cidr",
    "IP-CIDR6": "ip_cidr",
}


def _normalize_singbox_value(rule_type: str, value: str) -> str:
    if rule_type in {"IP-CIDR", "IP-CIDR6"}:
        return value.split(",", 1)[0].strip()
    return value


def render_singbox_rule_set(rules: list[Rule]) -> str:
    values_by_field: dict[str, list[str]] = {}
    seen_by_field: dict[str, set[str]] = {}
    for rule in rules:
        rule_type = SINGBOX_TYPE_ALIASES.get(rule.type, rule.type)
        field = SINGBOX_RULE_FIELDS.get(rule_type)
        if field is None:
            continue
        value = _normalize_singbox_value(rule_type, rule.value)
        seen = seen_by_field.setdefault(field, set())
        if value in seen:
            continue
        seen.add(value)
        values_by_field.setdefault(field, []).append(value)

    payload = {
        "version": 1,
        "rules": [
            {field: values}
            for field, values in values_by_field.items()
            if values
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
