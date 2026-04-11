from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from egloon_rule_hub.model.catalog import Catalog


def _services_markdown(catalog: Catalog) -> str:
    lines = [
        "# Services",
        "",
        f"Total services: {len(catalog.services)}",
        "",
        "| Service | Enabled | Targets | Sources | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, service in sorted(catalog.services.items()):
        service_link = f"[{name}](services/{name}.md)"
        lines.append(
            f"| {service_link} | {service.enabled} | {', '.join(service.targets)} |"
            f" {len(service.sources)} | {service.notes or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _sources_markdown(catalog: Catalog) -> str:
    lines = [
        "# Sources",
        "",
        "| Source | Kind | Repo | Branch | Base Raw URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, source in sorted(catalog.sources.items()):
        lines.append(
            f"| {name} | {source.kind} | {source.repo or '-'} |"
            f" {source.branch or '-'} | {source.base_raw_url or '-'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _usage_markdown(catalog: Catalog) -> str:
    bundle_names = ", ".join(sorted(catalog.bundles))
    lines = [
        "# Usage",
        "",
        "This repository is designed to publish both per-service and per-bundle artifacts.",
        "",
        "Expected artifact layout:",
        "",
        "- `dist/egern/<Service>.yaml`",
        "- `dist/loon/<Service>.list`",
        "- `dist/clash/<Service>.yaml`",
        "- `dist/quanx/<Service>.list`",
        "- `dist/shadowrocket/<Service>.list`",
        "- `dist/bundles/<bundle>/<target>.<ext>`",
        "",
        "Example raw URL pattern after publishing the repository:",
        "",
        "```text",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/loon/OpenAI.list",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/egern/OpenAI.yaml",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/dist/bundles/ai/loon.list",
        "```",
        "",
        f"Current bundles: {bundle_names}",
        "",
        "Use `python -m egloon_rule_hub render-rules` to refresh rule artifacts only.",
        "",
        "Use `python -m egloon_rule_hub bootstrap` after catalog changes to refresh rules, docs, and manifests together.",
        "",
    ]
    return "\n".join(lines)


def _attribution_markdown(catalog: Catalog) -> str:
    source_to_services: dict[str, set[str]] = {name: set() for name in catalog.sources}
    for service_name, service in sorted(catalog.services.items()):
        for source_ref in service.sources:
            source_to_services.setdefault(source_ref.source, set()).add(service_name)

    lines = [
        "# Attribution",
        "",
        "This repository republishes, transforms, or derives rule artifacts from upstream sources.",
        "Keep this file in public repositories so the upstream relationship stays visible.",
        "",
        "## Upstream Sources",
        "",
    ]

    for source_name, source in sorted(catalog.sources.items()):
        services = sorted(source_to_services.get(source_name, set()))
        lines.extend(
            [
                f"### {source_name}",
                "",
                f"- Kind: `{source.kind}`",
                f"- Repo: `{source.repo}`" if source.repo else "- Repo: `-`",
                f"- Branch: `{source.branch}`" if source.branch else "- Branch: `-`",
                (
                    f"- Base raw URL: `{source.base_raw_url}`"
                    if source.base_raw_url
                    else "- Base raw URL: `-`"
                ),
                f"- Referenced by services: {len(services)}",
            ]
        )
        if services:
            lines.append(f"- Services: {', '.join(services)}")
        else:
            lines.append("- Services: none yet")
        lines.append("")

    lines.extend(
        [
            "## Public Repository Note",
            "",
            "- This repository should keep upstream attribution visible in the README and this file.",
            "- Generated artifacts are transformed outputs, not claims of original authorship.",
            "- Before public release, review each upstream repository's license and redistribution terms.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_upstream_docs_manifest(root: Path) -> dict[str, list[dict[str, Any]]]:
    manifest_file = root / "dist" / "manifests" / "upstream_docs.json"
    if not manifest_file.exists():
        return {}

    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    manifest: dict[str, list[dict[str, Any]]] = {}
    for service_name, entries in payload.items():
        if not isinstance(service_name, str):
            continue
        if not isinstance(entries, list):
            manifest[service_name] = []
            continue
        manifest[service_name] = [
            entry for entry in entries if isinstance(entry, dict)
        ]
    return manifest


def _read_snapshot_text(root: Path, snapshot_path: str | None) -> str | None:
    if not snapshot_path:
        return None
    rel_path = Path(snapshot_path)
    if rel_path.is_absolute():
        return None

    root_resolved = root.resolve()
    snapshot_file = (root / rel_path).resolve()
    try:
        snapshot_file.relative_to(root_resolved)
    except ValueError:
        return None

    if not snapshot_file.exists() or not snapshot_file.is_file():
        return None

    try:
        return snapshot_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _markdown_code_fence(text: str) -> str:
    max_run = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, max_run + 1)


def _service_detail_markdown(
    root: Path,
    service_name: str,
    catalog: Catalog,
    entries: list[dict[str, Any]],
) -> str:
    service = catalog.services[service_name]
    lines = [
        f"# {service_name}",
        "",
        "## Service Summary",
        "",
        f"- Enabled: {service.enabled}",
        f"- Targets: {', '.join(service.targets)}",
        f"- Sources (catalog): {len(service.sources)}",
        f"- Notes: {service.notes or '-'}",
        "",
        "## Upstream README Sources",
        "",
    ]
    if not entries:
        lines.extend(
            [
                "- No upstream docs manifest entries.",
                "",
            ]
        )
        return "\n".join(lines)

    for index, entry in enumerate(entries, start=1):
        source = str(entry.get("source") or "-")
        rule_url = str(entry.get("rule_url") or "-")
        readme_url = str(entry.get("readme_url") or "-")
        status = str(entry.get("status") or "unknown")
        snapshot_path = entry.get("snapshot_path")
        snapshot_text = _read_snapshot_text(
            root,
            snapshot_path if isinstance(snapshot_path, str) else None,
        )

        lines.extend(
            [
                f"### Upstream Entry {index} ({source})",
                "",
                (
                    f"- Rule file: [{rule_url}]({rule_url})"
                    if rule_url != "-"
                    else "- Rule file: -"
                ),
                (
                    f"- README: [{readme_url}]({readme_url})"
                    if readme_url != "-"
                    else "- README: -"
                ),
                f"- Status: `{status}`",
                "",
            ]
        )

        if status == "ok":
            if snapshot_text is None:
                lines.append("upstream README missing snapshot")
                lines.append("")
            else:
                lines.extend(
                    [
                        "#### Upstream Original Text",
                        "",
                        f"{_markdown_code_fence(snapshot_text)}text",
                        snapshot_text.rstrip("\n"),
                        _markdown_code_fence(snapshot_text),
                        "",
                    ]
                )
        elif status == "missing":
            lines.append("upstream README missing")
            lines.append("")
        elif status == "fetch_error":
            lines.append("upstream README fetch_error")
            lines.append("")
        else:
            lines.append(f"upstream README {status}")
            lines.append("")

    return "\n".join(lines)


def write_markdown_docs(root: Path, catalog: Catalog) -> None:
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    services_dir = docs_dir / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    upstream_docs_manifest = _load_upstream_docs_manifest(root)

    (docs_dir / "services.md").write_text(_services_markdown(catalog), encoding="utf-8")
    (docs_dir / "sources.md").write_text(_sources_markdown(catalog), encoding="utf-8")
    (docs_dir / "usage.md").write_text(_usage_markdown(catalog), encoding="utf-8")
    (docs_dir / "attribution.md").write_text(
        _attribution_markdown(catalog), encoding="utf-8"
    )
    for service_name in sorted(catalog.services):
        detail = _service_detail_markdown(
            root,
            service_name,
            catalog,
            upstream_docs_manifest.get(service_name, []),
        )
        (services_dir / f"{service_name}.md").write_text(detail, encoding="utf-8")
