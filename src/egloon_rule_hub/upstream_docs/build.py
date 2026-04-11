"""Build helpers for upstream docs snapshots and manifest generation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from egloon_rule_hub.model.catalog import Catalog
from egloon_rule_hub.sources.registry import resolve_source_ref
from egloon_rule_hub.upstream_docs.fetch import ReadmeFetcher, fetch_readme

MAX_SLUG_LENGTH = 40
MAX_SOURCE_SEGMENT_LENGTH = 24
MAX_SERVICE_SEGMENT_LENGTH = 32


def _sanitize_segment(value: str, default: str, max_length: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = slug[:max_length]
    return slug or default


def _slugify_path(path: str) -> str:
    return _sanitize_segment(path, "root", MAX_SLUG_LENGTH)


def _entry_key(priority: int, source_name: str, rule_url: str, entry_index: int) -> str:
    path = urlparse(rule_url).path or "/"
    slug = _slugify_path(path)
    source_segment = _sanitize_segment(source_name, "source", MAX_SOURCE_SEGMENT_LENGTH)
    digest = hashlib.sha1(rule_url.encode("utf-8")).hexdigest()[:8]
    return f"{priority}-{source_segment}-{slug}-{digest}-{entry_index}"


def build_upstream_docs(
    catalog: Catalog, fetcher: ReadmeFetcher | None = None
) -> dict[str, list[dict[str, Any]]]:
    root = catalog.root
    docs_root = root / "dist" / "upstream-readmes"
    manifest_root = root / "dist" / "manifests"
    if docs_root.exists():
        shutil.rmtree(docs_root)
    docs_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, list[dict[str, Any]]] = {}
    for service_name, service in sorted(catalog.services.items()):
        entries: list[dict[str, Any]] = []
        service_dir = _sanitize_segment(service_name, "service", MAX_SERVICE_SEGMENT_LENGTH)
        for index, source_ref in enumerate(service.sources):
            source_def = catalog.sources[source_ref.source]
            resolved = resolve_source_ref(source_def, source_ref)
            result = fetch_readme(resolved.url, fetcher=fetcher)
            key = _entry_key(resolved.priority, resolved.source_name, resolved.url, index)
            snapshot_path: str | None = None
            if result.status == "ok" and result.content is not None:
                snapshot_file = docs_root / service_dir / key / "README.md"
                snapshot_file.parent.mkdir(parents=True, exist_ok=True)
                snapshot_file.write_bytes(result.content)
                snapshot_path = snapshot_file.relative_to(root).as_posix()
            entries.append(
                {
                    "source": resolved.source_name,
                    "priority": resolved.priority,
                    "rule_url": resolved.url,
                    "readme_url": result.readme_url,
                    "status": result.status,
                    "snapshot_path": snapshot_path,
                    "entry_key": key,
                }
            )
        manifest[service_name] = entries

    manifest_file = manifest_root / "upstream_docs.json"
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
