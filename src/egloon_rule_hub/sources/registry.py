from __future__ import annotations

from egloon_rule_hub.model.catalog import SourceDef, SourceRef
from egloon_rule_hub.sources.acl4ssr import resolve_acl4ssr
from egloon_rule_hub.sources.base import ResolvedSource, resolve_source
from egloon_rule_hub.sources.blackmatrix7 import resolve_blackmatrix7
from egloon_rule_hub.sources.generic_remote import resolve_remote
from egloon_rule_hub.sources.shadowrocket import resolve_shadowrocket

RESOLVERS = {
    "github_repo": resolve_source,
    "remote": resolve_remote,
    "blackmatrix7_repo": resolve_blackmatrix7,
    "acl4ssr_repo": resolve_acl4ssr,
    "shadowrocket_repo": resolve_shadowrocket,
}


def resolve_source_ref(source_def: SourceDef, source_ref: SourceRef) -> ResolvedSource:
    resolver = RESOLVERS.get(source_def.kind)
    if resolver is None:
        raise ValueError(f"Unsupported source kind: {source_def.kind}")
    return resolver(source_def, source_ref)

