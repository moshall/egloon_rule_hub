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

TARGET_DISPLAY_NAMES = {
    "clash": "Clash",
    "egern": "Egern",
    "loon": "Loon",
    "quanx": "QuanX",
    "shadowrocket": "Shadowrocket",
}

FORMAT_TO_NATIVE_TARGET = {
    "clash_yaml": "clash",
    "clash_list": "clash",
    "loon_list": "loon",
    "quanx_list": "quanx",
    "shadowrocket_list": "shadowrocket",
    "egern_yaml": "egern",
}


def _target_display_name(target: str) -> str:
    return TARGET_DISPLAY_NAMES.get(target, target.capitalize())


def _infer_native_target(format_name: str | None, rule_url: str) -> str | None:
    if format_name:
        mapped = FORMAT_TO_NATIVE_TARGET.get(format_name)
        if mapped:
            return mapped
    segments = [segment.lower() for segment in (urlparse(rule_url).path or "").split("/") if segment]
    for segment in segments:
        if segment in TARGET_DISPLAY_NAMES:
            return segment
    return None


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
        base_entries: list[dict[str, Any]] = []
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
            native_target = _infer_native_target(resolved.format, resolved.url)
            base_entries.append(
                {
                    "source": resolved.source_name,
                    "priority": resolved.priority,
                    "rule_url": resolved.url,
                    "readme_url": result.readme_url,
                    "status": result.status,
                    "snapshot_path": snapshot_path,
                    "entry_key": key,
                    "native_target": native_target,
                }
            )
        manifest_entries: list[dict[str, Any]] = []
        native_targets = {entry["native_target"] for entry in base_entries if entry["native_target"]}
        for target_name in service.targets:
            display_name = _target_display_name(target_name)
            is_converted = target_name not in native_targets
            if is_converted:
                relevant_entries = base_entries
            else:
                relevant_entries = [
                    entry for entry in base_entries if entry["native_target"] == target_name
                ]
            if not relevant_entries:
                continue
            for entry_data in relevant_entries:
                manifest_entries.append(
                    {
                        "target": target_name,
                        "target_dir": display_name,
                        "service": service_name,
                        "source": entry_data["source"],
                        "priority": entry_data["priority"],
                        "rule_url": entry_data["rule_url"],
                        "readme_url": entry_data["readme_url"],
                        "status": entry_data["status"],
                        "snapshot_path": entry_data["snapshot_path"],
                        "entry_key": entry_data["entry_key"],
                        "is_converted": is_converted,
                    }
                )
        manifest[service_name] = manifest_entries

    manifest_file = manifest_root / "upstream_docs.json"
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
