from __future__ import annotations

from dataclasses import dataclass, field

from egloon_rule_hub.model.rules import Rule


@dataclass(slots=True)
class SelectedSourceEntry:
    source_name: str
    family: str
    format: str | None
    url: str
    priority: int
    raw_text: str


@dataclass(slots=True)
class TargetArtifact:
    service: str
    target: str
    selected_family: str
    selected_native_target: str
    publish_mode: str | None
    is_native: bool
    is_converted: bool
    conversion_path: str | None
    origin_kind: str = "upstream"
    origin_source_path: str | None = None
    origin_source_url: str | None = None
    rules: list[Rule] = field(default_factory=list)
    selected_entries: list[SelectedSourceEntry] = field(default_factory=list)
