from __future__ import annotations

from egloon_rule_hub.model.rules import Rule


def dedupe_rules(rules: list[Rule]) -> list[Rule]:
    seen: set[tuple[str, str]] = set()
    output: list[Rule] = []
    for rule in rules:
        key = (rule.type, rule.value)
        if key in seen:
            continue
        seen.add(key)
        output.append(rule)
    return output

