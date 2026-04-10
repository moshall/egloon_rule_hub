from __future__ import annotations

from collections.abc import Iterable

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.normalize.dedupe import dedupe_rules


def merge_rule_streams(rule_streams: Iterable[list[Rule]]) -> list[Rule]:
    merged: list[Rule] = []
    for rule_stream in rule_streams:
        merged.extend(rule_stream)
    return dedupe_rules(merged)

