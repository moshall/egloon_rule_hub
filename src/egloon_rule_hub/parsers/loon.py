from __future__ import annotations

from egloon_rule_hub.model.rules import Rule


def parse_loon_list(content: str) -> list[Rule]:
    rules: list[Rule] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rule_type, value = line.split(",", 1)
        rules.append(Rule(rule_type.strip().upper(), value.strip()))
    return rules

