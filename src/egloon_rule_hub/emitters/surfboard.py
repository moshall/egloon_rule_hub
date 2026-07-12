from __future__ import annotations

from egloon_rule_hub.model.rules import Rule

SURFBOARD_TYPE_ALIASES = {
    "HOST": "DOMAIN",
    "HOST-SUFFIX": "DOMAIN-SUFFIX",
    "HOST-KEYWORD": "DOMAIN-KEYWORD",
    "IP6-CIDR": "IP-CIDR6",
}

SURFBOARD_RULE_TYPES = frozenset(
    {
        "DOMAIN",
        "DOMAIN-SUFFIX",
        "DOMAIN-KEYWORD",
        "DOMAIN-WILDCARD",
        "IP-CIDR",
        "IP-CIDR6",
        "GEOIP",
        "USER-AGENT",
        "DEST-PORT",
        "SRC-IP",
        "IN-PORT",
        "PROTOCOL",
    }
)


def _normalize_surfboard_rule(rule: Rule) -> Rule | None:
    rule_type = SURFBOARD_TYPE_ALIASES.get(rule.type, rule.type)
    if rule_type not in SURFBOARD_RULE_TYPES:
        return None
    value = rule.value
    if rule_type in {"IP-CIDR", "IP-CIDR6"}:
        value = value.split(",", 1)[0].strip()
    return Rule(rule_type, value)


def render_surfboard_rules(rules: list[Rule]) -> str:
    rendered_rules = [
        normalized.render()
        for rule in rules
        if (normalized := _normalize_surfboard_rule(rule)) is not None
    ]
    return "\n".join(rendered_rules) + ("\n" if rendered_rules else "")
