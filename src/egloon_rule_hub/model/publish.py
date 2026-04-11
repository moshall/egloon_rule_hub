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
class TargetArtifactVariant:
    name: str
    primary: bool
    selected_family: str
    selected_native_target: str
    publish_mode: str | None
    is_native: bool
    is_converted: bool
    conversion_path: str | None
    rules: list[Rule] = field(default_factory=list)
    selected_entries: list[SelectedSourceEntry] = field(default_factory=list)


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
    primary_variant_name: str | None = None
    variants: dict[str, TargetArtifactVariant] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.primary_variant_name:
            self.primary_variant_name = self.service
        if not self.variants:
            self.variants = {
                self.primary_variant_name: TargetArtifactVariant(
                    name=self.primary_variant_name,
                    primary=True,
                    selected_family=self.selected_family,
                    selected_native_target=self.selected_native_target,
                    publish_mode=self.publish_mode,
                    is_native=self.is_native,
                    is_converted=self.is_converted,
                    conversion_path=self.conversion_path,
                    rules=list(self.rules),
                    selected_entries=list(self.selected_entries),
                )
            }
