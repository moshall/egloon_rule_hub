from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
import ipaddress
from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.normalize.dedupe import dedupe_rules

_METADATA_PATTERN = re.compile(r"^#\s*@([A-Za-z0-9_]+):\s*(.*)$")
_CIDR_PATTERN = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}$")
_DOMAIN_PATTERN = re.compile(
    r"^(?!-)(?:[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?\.)+[A-Za-z]{2,}$",
    re.IGNORECASE,
)


@dataclass(slots=True)
class TxtServiceSnapshot:
    service_name: str
    source_path: Path
    metadata: dict[str, str]
    rules: list[Rule]


def discover_txt_services(
    root: Path,
    failures: dict[str, str] | None = None,
) -> list[TxtServiceSnapshot]:
    txt_dir = root / "Source" / "TXT"
    if not txt_dir.exists() or not txt_dir.is_dir():
        return []

    snapshots: list[TxtServiceSnapshot] = []
    for source_path in sorted(txt_dir.iterdir()):
        if not source_path.is_file():
            continue
        if source_path.suffix.lower() != ".txt":
            continue
        try:
            metadata, rules = parse_txt_service_text(
                source_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            if failures is not None:
                try:
                    failure_key = source_path.relative_to(root).as_posix()
                except ValueError:
                    failure_key = str(source_path)
                failures[failure_key] = str(exc)
            continue
        snapshots.append(
            TxtServiceSnapshot(
                service_name=source_path.stem,
                source_path=source_path,
                metadata=metadata,
                rules=rules,
            )
        )
    return snapshots


def parse_txt_service_text(text: str) -> tuple[dict[str, str], list[Rule]]:
    metadata: dict[str, str] = {}
    rules: list[Rule] = []
    text = text.lstrip("\ufeff")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            if metadata_match := _METADATA_PATTERN.match(line):
                key = metadata_match.group(1).strip().lower()
                value = metadata_match.group(2).strip()
                metadata[key] = value
            continue

        if rule := _normalize_rule_line(line):
            rules.append(rule)

    return metadata, dedupe_rules(rules)


def _normalize_rule_line(line: str) -> Rule | None:
    if "," in line:
        rule_type, value = (part.strip() for part in line.split(",", 1))
        if not rule_type or not value:
            return None
        return Rule(rule_type.upper(), value)

    if _CIDR_PATTERN.fullmatch(line) and _is_valid_cidr(line):
        return Rule("IP-CIDR", line)

    if _DOMAIN_PATTERN.fullmatch(line):
        return Rule("DOMAIN-SUFFIX", line)

    return None


def _is_valid_cidr(value: str) -> bool:
    try:
        ipaddress.IPv4Network(value, strict=False)
        return True
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError):
        return False
