from __future__ import annotations

from dataclasses import dataclass

from egloon_rule_hub.model.rules import Rule


@dataclass(frozen=True, slots=True)
class V2FlyDomainList:
    rules: list[Rule]
    includes: list[str]


def _without_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def _without_attributes(line: str) -> str:
    return line.split(" @", 1)[0].strip()


def parse_v2fly_domain_list(text: str) -> V2FlyDomainList:
    rules: list[Rule] = []
    includes: list[str] = []

    for raw_line in text.splitlines():
        line = _without_attributes(_without_comment(raw_line))
        if not line:
            continue
        if line.startswith("include:"):
            include_name = line.removeprefix("include:").strip()
            if include_name:
                includes.append(include_name)
            continue
        if line.startswith("full:"):
            rules.append(Rule("DOMAIN", line.removeprefix("full:").strip()))
            continue
        if line.startswith("regexp:"):
            rules.append(
                Rule("DOMAIN-REGEX", line.removeprefix("regexp:").strip())
            )
            continue
        rules.append(Rule("DOMAIN-SUFFIX", line))

    return V2FlyDomainList(rules=rules, includes=includes)
