from __future__ import annotations

from egloon_rule_hub.model.rules import Rule


def render_quanx_rules(rules: list[Rule]) -> str:
    return "\n".join(rule.render() for rule in rules) + ("\n" if rules else "")

