from __future__ import annotations

from collections.abc import Sequence

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.parsers.loon import extract_loon_sections


def _rule_heading_map(source_texts: Sequence[str]) -> tuple[dict[str, str], bool]:
    heading_by_rule: dict[str, str] = {}
    has_headings = False
    for source_text in source_texts:
        for section in extract_loon_sections(source_text):
            if section.heading is None:
                continue
            has_headings = True
            for rule in section.rules:
                heading_by_rule.setdefault(rule.render(), section.heading)
    return heading_by_rule, has_headings


def render_loon_lsr(
    service_name: str, rules: list[Rule], source_texts: Sequence[str] | None = None
) -> str:
    if not rules:
        return ""

    heading_by_rule, has_headings = _rule_heading_map(source_texts or [])
    lines: list[str] = []
    if not has_headings:
        lines.append(f"# > {service_name}")
        lines.extend(rule.render() for rule in rules)
        return "\n".join(lines) + "\n"

    current_heading: str | None = None
    for rule in rules:
        rendered_rule = rule.render()
        heading = heading_by_rule.get(rendered_rule)
        if heading is not None and heading != current_heading:
            if lines:
                lines.append("")
            lines.append(f"# {heading}")
            current_heading = heading
        lines.append(rendered_rule)
    return "\n".join(lines) + "\n"
