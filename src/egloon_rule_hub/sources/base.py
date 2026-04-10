from __future__ import annotations

from dataclasses import dataclass

from egloon_rule_hub.model.catalog import SourceDef, SourceRef


@dataclass(slots=True)
class ResolvedSource:
    source_name: str
    url: str
    format: str | None
    priority: int


def resolve_source(source_def: SourceDef, source_ref: SourceRef) -> ResolvedSource:
    if source_ref.url:
        return ResolvedSource(
            source_name=source_ref.source,
            url=source_ref.url,
            format=source_ref.format,
            priority=source_ref.priority,
        )
    if source_def.base_raw_url and source_ref.path:
        return ResolvedSource(
            source_name=source_ref.source,
            url=f"{source_def.base_raw_url.rstrip('/')}/{source_ref.path.lstrip('/')}",
            format=source_ref.format,
            priority=source_ref.priority,
        )
    raise ValueError(f"Unable to resolve source {source_ref.source}")

