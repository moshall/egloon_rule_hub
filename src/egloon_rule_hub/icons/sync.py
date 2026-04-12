from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from egloon_rule_hub.model.catalog import Catalog
from egloon_rule_hub.model.publish import TargetArtifact

ICON_TREE_URL = "https://api.github.com/repos/Keviin560/icon/git/trees/main?recursive=1"
ICON_RAW_BASE_URL = "https://raw.githubusercontent.com/Keviin560/icon/main/"

TARGET_DISPLAY_NAMES = {
    "clash": "Clash",
    "egern": "Egern",
    "loon": "Loon",
    "quantumultx": "QuantumultX",
    "shadowrocket": "Shadowrocket",
}

IconPathLister = Callable[[], list[str]]
IconBytesFetcher = Callable[[str], bytes]


def _http_get(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "egloon-rule-hub/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read()


def list_remote_icon_paths() -> list[str]:
    payload = json.loads(_http_get(ICON_TREE_URL).decode("utf-8"))
    tree = payload.get("tree", [])
    if not isinstance(tree, list):
        raise ValueError("invalid icon tree payload")

    icon_paths: list[str] = []
    for entry in tree:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        entry_type = entry.get("type")
        if not isinstance(path, str) or entry_type != "blob":
            continue
        if not path.startswith("src/") or not path.endswith(".png"):
            continue
        if len(Path(path).parts) != 2:
            continue
        icon_paths.append(path)
    return sorted(icon_paths)


def fetch_remote_icon_bytes(source_path: str) -> bytes:
    quoted_path = quote(source_path, safe="/")
    return _http_get(f"{ICON_RAW_BASE_URL}{quoted_path}")


def _manifest_path(root: Path) -> Path:
    return root / "dist" / "manifests" / "icons.json"


def _load_previous_manifest(root: Path) -> dict[str, dict[str, Any]]:
    manifest_path = _manifest_path(root)
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        service_name: entry
        for service_name, entry in payload.items()
        if isinstance(service_name, str) and isinstance(entry, dict)
    }


def _service_icon_entry(
    *,
    matched: bool,
    reason: str | None,
    source_path: str | None,
    published_paths: list[str],
) -> dict[str, Any]:
    return {
        "matched": matched,
        "reason": reason,
        "source_path": source_path,
        "source_url": (
            f"{ICON_RAW_BASE_URL}{quote(source_path, safe='/')}" if source_path else None
        ),
        "published_paths": published_paths,
    }


def _prune_generated_icon_paths(
    root: Path,
    previous_entry: dict[str, Any] | None,
    keep_paths: set[str] | None = None,
) -> None:
    if not previous_entry or not previous_entry.get("matched"):
        return

    for rel_path in previous_entry.get("published_paths", []):
        if not isinstance(rel_path, str):
            continue
        if keep_paths is not None and rel_path in keep_paths:
            continue
        icon_path = root / rel_path
        if icon_path.exists() and icon_path.is_file():
            icon_path.unlink()
        current = icon_path.parent
        rule_root = root / "Rule"
        while current.exists() and current != rule_root:
            try:
                if any(current.iterdir()):
                    break
            except OSError:
                break
            current.rmdir()
            current = current.parent


def sync_service_icons(
    root: Path,
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]],
    *,
    list_icon_paths: IconPathLister = list_remote_icon_paths,
    fetch_icon_bytes: IconBytesFetcher = fetch_remote_icon_bytes,
) -> dict[str, dict[str, Any]]:
    manifest_root = _manifest_path(root)
    manifest_root.parent.mkdir(parents=True, exist_ok=True)

    previous_manifest = _load_previous_manifest(root)
    services = sorted(target_artifacts)
    manifest: dict[str, dict[str, Any]] = {}

    try:
        available_paths = list_icon_paths()
    except Exception:
        for service_name in services:
            manifest[service_name] = _service_icon_entry(
                matched=False,
                reason="icon_sync_source_unavailable",
                source_path=None,
                published_paths=[],
            )
        manifest_root.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return manifest

    exact_match_paths = {Path(path).stem: path for path in available_paths}
    for service_name in services:
        source_path = exact_match_paths.get(service_name)
        previous_entry = previous_manifest.get(service_name)
        if not source_path:
            _prune_generated_icon_paths(root, previous_entry, keep_paths=set())
            manifest[service_name] = _service_icon_entry(
                matched=False,
                reason="strict_match_not_found",
                source_path=None,
                published_paths=[],
            )
            continue

        try:
            icon_bytes = fetch_icon_bytes(source_path)
        except Exception:
            manifest[service_name] = _service_icon_entry(
                matched=False,
                reason="icon_sync_source_unavailable",
                source_path=None,
                published_paths=[],
            )
            continue

        published_paths: list[str] = []
        for target_name in sorted(target_artifacts.get(service_name, {})):
            display_target = TARGET_DISPLAY_NAMES.get(target_name, target_name.capitalize())
            service_dir = root / "Rule" / display_target / service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            icon_path = service_dir / "icon.png"
            icon_path.write_bytes(icon_bytes)
            published_paths.append(icon_path.relative_to(root).as_posix())

        keep_paths = set(published_paths)
        _prune_generated_icon_paths(root, previous_entry, keep_paths=keep_paths)
        manifest[service_name] = _service_icon_entry(
            matched=True,
            reason=None,
            source_path=source_path,
            published_paths=published_paths,
        )

    for service_name, previous_entry in previous_manifest.items():
        if service_name in manifest:
            continue
        _prune_generated_icon_paths(root, previous_entry, keep_paths=set())

    manifest_root.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
