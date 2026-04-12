from __future__ import annotations

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.parsers.common import parse_standard_or_raw_rule


def parse_shadowrocket_list(content: str) -> list[Rule]:
    rules: list[Rule] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(parse_standard_or_raw_rule(line))
    return rules
