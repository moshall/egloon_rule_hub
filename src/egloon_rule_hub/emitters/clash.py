from __future__ import annotations

import yaml

from egloon_rule_hub.model.rules import Rule


def render_clash_rule_provider(rules: list[Rule]) -> str:
    payload = {"payload": [rule.render() for rule in rules]}
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

