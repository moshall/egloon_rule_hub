from __future__ import annotations

import yaml

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.parsers.common import parse_standard_or_raw_rule


def parse_clash_rule_provider(content: str) -> list[Rule]:
    data = yaml.safe_load(content) or {}
    payload = data.get("payload", [])
    rules: list[Rule] = []
    for item in payload:
        rules.append(parse_standard_or_raw_rule(str(item)))
    return rules
