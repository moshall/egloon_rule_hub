from __future__ import annotations

import yaml

from egloon_rule_hub.model.rules import Rule


def parse_clash_rule_provider(content: str) -> list[Rule]:
    data = yaml.safe_load(content) or {}
    payload = data.get("payload", [])
    rules: list[Rule] = []
    for item in payload:
        rule_type, value = str(item).split(",", 1)
        rules.append(Rule(rule_type.strip().upper(), value.strip()))
    return rules

