from __future__ import annotations

from egloon_rule_hub.model.catalog import SourceDef, SourceRef
from egloon_rule_hub.sources.base import ResolvedSource, resolve_source


def resolve_shadowrocket(source_def: SourceDef, source_ref: SourceRef) -> ResolvedSource:
    return resolve_source(source_def, source_ref)

