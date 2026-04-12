from __future__ import annotations

from dataclasses import dataclass

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.parsers.common import parse_standard_or_raw_rule


@dataclass(slots=True)
class LoonSection:
    heading: str | None
    rules: list[Rule]


def _parse_loon_rule_line(line: str) -> Rule:
    return parse_standard_or_raw_rule(line)


def extract_loon_sections(content: str) -> list[LoonSection]:
    sections: list[LoonSection] = []
    current_heading: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            if heading:
                current_heading = heading
            continue

        rule = _parse_loon_rule_line(line)
        if sections and sections[-1].heading == current_heading:
            sections[-1].rules.append(rule)
            continue
        sections.append(LoonSection(heading=current_heading, rules=[rule]))

    return sections


def parse_loon_list(content: str) -> list[Rule]:
    rules: list[Rule] = []
    for section in extract_loon_sections(content):
        rules.extend(section.rules)
    return rules
