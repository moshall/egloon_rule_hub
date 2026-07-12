"""Build helpers for upstream docs snapshots and manifest generation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from egloon_rule_hub.model.catalog import Catalog
from egloon_rule_hub.model.publish import TargetArtifact
from egloon_rule_hub.upstream_docs.fetch import ReadmeFetcher, derive_readme_url, fetch_readme

MAX_SLUG_LENGTH = 40
MAX_SOURCE_SEGMENT_LENGTH = 24
MAX_SERVICE_SEGMENT_LENGTH = 32

TARGET_DISPLAY_NAMES = {
    "clash": "Clash",
    "egern": "Egern",
    "loon": "Loon",
    "quantumultx": "QuantumultX",
    "shadowrocket": "Shadowrocket",
    "surfboard": "Surfboard",
    "singbox": "SingBox",
}

def _target_display_name(target: str) -> str:
    return TARGET_DISPLAY_NAMES.get(target, target.capitalize())


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


def _snapshot_key(readme_url: str) -> str:
    parsed = urlparse(readme_url)
    slug = _slugify_path(parsed.path or "/")
    digest = hashlib.sha1(readme_url.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}"


def _artifact_output_ext(target: str, publish_mode: str | None) -> str:
    if target == "loon" and publish_mode == "lsr":
        return "lsr"
    return {
        "clash": "yaml",
        "egern": "yaml",
        "loon": "list",
        "quantumultx": "list",
        "shadowrocket": "list",
        "surfboard": "list",
        "singbox": "json",
    }.get(target, "list")


def _prune_stale_snapshots(docs_root: Path, live_snapshot_paths: set[Path]) -> None:
    if not docs_root.exists():
        return
    for path in sorted(docs_root.rglob("*"), reverse=True):
        if path.is_file():
            if path not in live_snapshot_paths:
                path.unlink()
            continue
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def build_upstream_docs(
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]] | None = None,
    fetcher: ReadmeFetcher | None = None,
) -> dict[str, list[dict[str, Any]]]:
    if target_artifacts is None:
        from egloon_rule_hub.build import build_all_target_artifacts

        target_artifacts = build_all_target_artifacts(catalog)

    root = catalog.root
    docs_root = root / "dist" / "upstream-readmes"
    manifest_root = root / "dist" / "manifests"
    docs_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, list[dict[str, Any]]] = {}
    live_snapshot_paths: set[Path] = set()
    readme_cache: dict[str, tuple[str, str, str | None]] = {}
    for service_name, service in sorted(catalog.services.items()):
        manifest_entries: list[dict[str, Any]] = []
        service_artifacts = target_artifacts.get(service_name, {})
        entry_index = 0
        for target_name in service.targets:
            artifact = service_artifacts.get(target_name)
            if artifact is None:
                continue
            display_name = _target_display_name(target_name)
            for variant_name, variant in artifact.variants.items():
                variant_file = f"{variant_name}.{_artifact_output_ext(target_name, variant.publish_mode)}"
                for selected_entry in variant.selected_entries:
                    readme_url = derive_readme_url(selected_entry.url)
                    cached_result = readme_cache.get(readme_url)
                    if cached_result is None:
                        result = fetch_readme(selected_entry.url, fetcher=fetcher)
                        snapshot_path: str | None = None
                        if result.status == "ok" and result.content is not None:
                            snapshot_file = docs_root / _snapshot_key(result.readme_url) / "README.md"
                            snapshot_file.parent.mkdir(parents=True, exist_ok=True)
                            snapshot_file.write_bytes(result.content)
                            live_snapshot_paths.add(snapshot_file)
                            snapshot_path = snapshot_file.relative_to(root).as_posix()
                        readme_cache[readme_url] = (result.readme_url, result.status, snapshot_path)
                    else:
                        result_readme_url, result_status, snapshot_path = cached_result
                        if snapshot_path is not None:
                            live_snapshot_paths.add(root / snapshot_path)
                    key = _entry_key(
                        selected_entry.priority,
                        selected_entry.source_name,
                        selected_entry.url,
                        entry_index,
                    )
                    entry_index += 1
                    if cached_result is None:
                        result_readme_url = result.readme_url
                        result_status = result.status
                    manifest_entries.append(
                        {
                            "target": target_name,
                            "target_dir": display_name,
                            "service": service_name,
                            "variant": variant_name,
                            "variant_primary": variant.primary,
                            "variant_file": variant_file,
                            "publish_mode": variant.publish_mode,
                            "selected_family": variant.selected_family,
                            "selected_native_target": variant.selected_native_target,
                            "is_native": variant.is_native,
                            "is_converted": variant.is_converted,
                            "conversion_path": variant.conversion_path,
                            "source": selected_entry.source_name,
                            "priority": selected_entry.priority,
                            "rule_url": selected_entry.url,
                            "readme_url": result_readme_url,
                            "status": result_status,
                            "snapshot_path": snapshot_path,
                            "entry_key": key,
                        }
                    )
        manifest[service_name] = manifest_entries

    _prune_stale_snapshots(docs_root, live_snapshot_paths)

    manifest_file = manifest_root / "upstream_docs.json"
    manifest_file.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
