from __future__ import annotations

import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from egloon_rule_hub.model.catalog import Catalog, ServiceDef, SourceRef, TargetDef
from egloon_rule_hub.model.publish import TargetArtifact

TARGET_DISPLAY_NAMES = {
    "clash": "Clash",
    "egern": "Egern",
    "loon": "Loon",
    "quantumultx": "QuantumultX",
    "shadowrocket": "Shadowrocket",
    "surfboard": "Surfboard",
    "singbox": "SingBox",
}

BUNDLE_DISPLAY_NAMES = {
    "ai": "AI",
}


def _target_display_name(target: str) -> str:
    return TARGET_DISPLAY_NAMES.get(target, target.capitalize())


def _bundle_display_name(
    bundle_name: str,
    service_names: set[str] | None = None,
) -> str:
    explicit = BUNDLE_DISPLAY_NAMES.get(bundle_name)
    if explicit:
        return explicit
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", bundle_name) if part]
    if not parts:
        display_name = bundle_name
    else:
        display_name = "".join(part[:1].upper() + part[1:] for part in parts)
    if service_names and display_name in service_names:
        return f"{display_name}Bundle"
    return display_name


def _source_ref_key(source_ref: SourceRef) -> tuple[str, str | None, str | None, str | None]:
    return (
        source_ref.source,
        source_ref.path,
        source_ref.url,
        source_ref.format,
    )


def service_source_count(service: ServiceDef) -> int:
    distinct_refs: set[tuple[str, str | None, str | None, str | None]] = set()
    if service.target_sources:
        for target_source in service.target_sources.values():
            for variant in target_source.normalized_variants(service.name).values():
                for family_sources in variant.families.values():
                    for source_ref in family_sources:
                        distinct_refs.add(_source_ref_key(source_ref))
    else:
        for source_ref in service.sources:
            distinct_refs.add(_source_ref_key(source_ref))
    return len(distinct_refs)


def _services_markdown(
    catalog: Catalog,
    service_readme_paths: dict[str, list[str]],
) -> str:
    lines = [
        "# Services",
        "",
        f"Total services: {len(catalog.services)}",
        "",
        "| Service | Enabled | Targets | Sources | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, service in sorted(catalog.services.items()):
        lines.append(
            f"| {name} | {service.enabled} | {', '.join(service.targets)} |"
            f" {service_source_count(service)} | {service.notes or '-'} |"
        )
    lines.append("")
    lines.extend(
        [
            "## Target READMEs",
            "",
        ]
    )
    for service_name in sorted(catalog.services):
        readmes = service_readme_paths.get(service_name, [])
        if readmes:
            lines.append(f"- {service_name}")
            for readme_path in readmes:
                lines.append(f"  - [{readme_path}]({readme_path})")
        else:
            lines.append(f"- {service_name}: (no target README yet)")
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
        (
            "Each per-service target publishes a directory under "
            "`Rule/<TargetDir>/<Service>/` that pairs the target artifact with a "
            "README describing the selected source family and any conversion path."
        ),
        "",
        "Expected artifact layout:",
        "",
        "- `Rule/Clash/OpenAI/OpenAI.yaml`",
        "- `Rule/Loon/OpenAI/OpenAI.lsr`",
        "- `Rule/Egern/OpenAI/OpenAI.yaml`",
        "- `Rule/QuantumultX/OpenAI/OpenAI.list`",
        "- `Rule/Shadowrocket/OpenAI/OpenAI.list`",
        "- `Rule/Clash/AI/AI.yaml`",
        "- `Rule/Loon/AI/AI.lsr`",
        "- `Rule/QuantumultX/ChinaBank/ChinaBank.list`",
        "",
        "Example raw URL pattern after publishing the repository:",
        "",
        "```text",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Clash/OpenAI/OpenAI.yaml",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Loon/OpenAI/OpenAI.lsr",
        "https://raw.githubusercontent.com/<owner>/<repo>/<branch>/Rule/Loon/AI/AI.lsr",
        "```",
        "",
        "Selection policy: choose the first non-empty family in `native -> shadowrocket -> clash`, then merge only within that selected family.",
        "Bundle policy: merge only the primary published variant from each member service, then normalize and deduplicate the combined stream.",
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
        seen_sources: set[str] = set()
        if service.target_sources:
            for target_source in service.target_sources.values():
                for variant in target_source.normalized_variants(service.name).values():
                    for family_sources in variant.families.values():
                        for source_ref in family_sources:
                            if source_ref.source not in seen_sources:
                                source_to_services.setdefault(source_ref.source, set()).add(
                                    service_name
                                )
                                seen_sources.add(source_ref.source)
        else:
            for source_ref in service.sources:
                if source_ref.source in seen_sources:
                    continue
                source_to_services.setdefault(source_ref.source, set()).add(service_name)
                seen_sources.add(source_ref.source)

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


def _load_icons_manifest(root: Path) -> dict[str, dict[str, Any]]:
    manifest_file = root / "dist" / "manifests" / "icons.json"
    if not manifest_file.exists():
        return {}

    try:
        payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    return {
        service_name: entry
        for service_name, entry in payload.items()
        if isinstance(service_name, str) and isinstance(entry, dict)
    }


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


def _group_manifest_entries_by_target(
    manifest: dict[str, list[dict[str, Any]]]
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for service_name, entries in manifest.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target")
            if not isinstance(target, str) or not target.strip():
                continue
            target_dir = entry.get("target_dir")
            if not isinstance(target_dir, str) or not target_dir.strip():
                target_dir = _target_display_name(target)
            service = entry.get("service")
            if not isinstance(service, str) or not service.strip():
                service = service_name
            key = (target, target_dir, service)
            grouped[key].append(entry)
    return grouped


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


def _bundle_output_file(
    bundle_name: str,
    target: str,
    publish_mode: str | None,
    catalog: Catalog | None = None,
) -> str:
    service_names = set(catalog.services) if catalog is not None else None
    bundle_display = _bundle_display_name(bundle_name, service_names)
    return f"{bundle_display}.{_artifact_output_ext(target, publish_mode)}"


def _bundle_service_variant_details(
    catalog: Catalog,
    service_name: str,
    target_name: str,
    target_artifacts: dict[str, dict[str, TargetArtifact]] | None,
) -> tuple[str, list[str]]:
    artifact = None
    if target_artifacts is not None:
        artifact = target_artifacts.get(service_name, {}).get(target_name)
    if artifact is not None:
        primary_variant = artifact.primary_variant_name or service_name
        extra_variants = [
            variant_name
            for variant_name in artifact.variants
            if variant_name != primary_variant
        ]
        return primary_variant, extra_variants

    service = catalog.services.get(service_name)
    if service is None:
        return service_name, []
    target_source = service.target_sources.get(target_name)
    if target_source is None:
        return service_name, []
    variants = target_source.normalized_variants(service_name)
    primary_variant = next(
        (variant.name for variant in variants.values() if variant.primary),
        service_name,
    )
    extra_variants = [
        variant.name for variant in variants.values() if variant.name != primary_variant
    ]
    return primary_variant, extra_variants


def _entry_variant_name(entry: dict[str, Any], service_name: str) -> str:
    variant = entry.get("variant")
    if isinstance(variant, str) and variant.strip():
        return variant
    return service_name


def _entry_variant_file(
    entry: dict[str, Any],
    target: str,
    publish_mode: str | None,
    variant_name: str,
) -> str:
    variant_file = entry.get("variant_file")
    if isinstance(variant_file, str) and variant_file.strip():
        return variant_file
    return f"{variant_name}.{_artifact_output_ext(target, publish_mode)}"


def _variant_usage_note(snapshot_text: str | None, variant_name: str, primary: bool) -> str:
    if snapshot_text:
        for raw_line in snapshot_text.splitlines():
            line = raw_line.strip().lstrip("-*").strip()
            if variant_name.lower() in line.lower():
                return line
    if primary:
        return "Primary published variant used for bundle merges."
    return "Additional published variant for manual selection."


def _icon_line(icon_manifest: dict[str, dict[str, Any]], service_name: str) -> str:
    icon_entry = icon_manifest.get(service_name)
    if not icon_entry:
        return "- Icon: unavailable"

    if bool(icon_entry.get("matched")):
        source_url = icon_entry.get("source_url")
        if isinstance(source_url, str) and source_url.strip():
            return f"- Icon: [icon.png](./icon.png) ([upstream source]({source_url}))"
        return "- Icon: [icon.png](./icon.png)"

    reason = icon_entry.get("reason")
    reason_text = {
        "strict_match_not_found": "strict upstream match not found",
        "icon_sync_source_unavailable": "icon sync source unavailable",
    }.get(reason, "unavailable")
    return f"- Icon: unavailable ({reason_text})"


def _target_readme_markdown(
    root: Path,
    target: str,
    target_dir: str,
    service_name: str,
    entries: list[dict[str, Any]],
    artifact: TargetArtifact | None = None,
    icon_manifest: dict[str, dict[str, Any]] | None = None,
) -> str:
    primary_entry = next(
        (entry for entry in entries if entry.get("variant_primary")),
        entries[0] if entries else None,
    )
    primary_variant = None
    if artifact is not None and artifact.primary_variant_name is not None:
        primary_variant = artifact.variants.get(artifact.primary_variant_name)

    selected_family = (
        str(primary_entry.get("selected_family") or "-")
        if primary_entry is not None
        else primary_variant.selected_family
        if primary_variant is not None
        else artifact.selected_family
        if artifact is not None
        else "-"
    )
    selected_native_target = (
        str(primary_entry.get("selected_native_target") or target)
        if primary_entry is not None
        else primary_variant.selected_native_target
        if primary_variant is not None
        else artifact.selected_native_target
        if artifact is not None
        else target
    )
    selected_native_target_dir = _target_display_name(selected_native_target)
    publish_mode = (
        primary_entry.get("publish_mode")
        if primary_entry is not None
        else primary_variant.publish_mode
        if primary_variant is not None
        else artifact.publish_mode
        if artifact is not None
        else None
    )
    conversion_path = (
        primary_entry.get("conversion_path")
        if primary_entry is not None
        else primary_variant.conversion_path
        if primary_variant is not None
        else artifact.conversion_path
        if artifact is not None
        else None
    )
    lines: list[str] = [
        f"# {service_name} for {target_dir}",
        "",
        f"This README documents the {target_dir} target derived for {service_name}.",
        "",
    ]
    if any(not entry.get("is_converted") for entry in entries) or (
        artifact is not None and not artifact.is_converted
    ):
        lines.append(
            f"This directory mirrors the direct upstream {target_dir} target for {service_name}."
        )
        lines.append("")
        lines.append("This layout documents a direct upstream target.")
        lines.append("")
    else:
        lines.append(
            f"This README is generated by egloon_rule_hub and is not a native upstream {target_dir} artifact."
        )
        lines.append("")

    lines.extend(
        [
            f"- Selected source family: `{selected_family}`",
            f"- Upstream native target: `{selected_native_target_dir}`",
        ]
    )
    if icon_manifest is not None:
        lines.append(_icon_line(icon_manifest, service_name))
    if publish_mode:
        lines.append(f"- Publish mode: `{publish_mode}`")
    if conversion_path:
        lines.append(f"- Conversion path: `{conversion_path}`")
    lines.append("")

    variant_entries: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        variant_entries[_entry_variant_name(entry, service_name)].append(entry)

    variant_names: list[str] = []
    if artifact is not None:
        variant_names.extend(artifact.variants.keys())
    for variant_name in variant_entries:
        if variant_name not in variant_names:
            variant_names.append(variant_name)
    if not variant_names:
        variant_names.append(service_name)

    lines.extend(
        [
            "## Published Variants",
            "",
        ]
    )
    for variant_name in variant_names:
        variant = artifact.variants.get(variant_name) if artifact is not None else None
        manifest_entries = variant_entries.get(variant_name, [])
        variant_primary = variant.primary if variant is not None else any(
            bool(entry.get("variant_primary")) for entry in manifest_entries
        )
        variant_publish_mode = (
            variant.publish_mode
            if variant is not None
            else manifest_entries[0].get("publish_mode")
            if manifest_entries
            else publish_mode
        )
        variant_file = (
            _entry_variant_file(manifest_entries[0], target, variant_publish_mode, variant_name)
            if manifest_entries
            else f"{variant_name}.{_artifact_output_ext(target, variant_publish_mode)}"
        )
        variant_selected_family = (
            variant.selected_family
            if variant is not None
            else str(manifest_entries[0].get("selected_family") or "-")
            if manifest_entries
            else "-"
        )
        variant_native_target = (
            variant.selected_native_target
            if variant is not None
            else str(manifest_entries[0].get("selected_native_target") or target)
            if manifest_entries
            else target
        )
        variant_conversion_path = (
            variant.conversion_path
            if variant is not None
            else manifest_entries[0].get("conversion_path")
            if manifest_entries
            else None
        )
        snapshot_text = None
        for entry in manifest_entries:
            snapshot_path = entry.get("snapshot_path")
            snapshot_text = _read_snapshot_text(
                root,
                snapshot_path if isinstance(snapshot_path, str) else None,
            )
            if snapshot_text is not None:
                break

        lines.extend(
            [
                f"### {variant_name}",
                "",
                f"- File: [{variant_file}](./{variant_file})",
                f"- Primary variant: `{'yes' if variant_primary else 'no'}`",
                f"- Usage note: {_variant_usage_note(snapshot_text, variant_name, variant_primary)}",
                f"- Selected source family: `{variant_selected_family}`",
                f"- Upstream native target: `{_target_display_name(variant_native_target)}`",
            ]
        )
        if variant_conversion_path:
            lines.append(f"- Conversion path: `{variant_conversion_path}`")
        rule_urls = [
            str(entry.get("rule_url") or "-")
            for entry in manifest_entries
            if str(entry.get("rule_url") or "-") != "-"
        ]
        if not rule_urls and variant is not None:
            rule_urls = [selected_entry.url for selected_entry in variant.selected_entries]
        for rule_url in rule_urls:
            lines.append(f"- Rule file: [{rule_url}]({rule_url})")
        lines.append("")

    lines.extend(
        [
            "## Upstream README Sources",
            "",
        ]
    )

    sorted_entries = sorted(entries, key=lambda entry: entry.get("priority") or 0)
    for index, entry in enumerate(sorted_entries, start=1):
        source = str(entry.get("source") or "-")
        rule_url = str(entry.get("rule_url") or "-")
        readme_url = str(entry.get("readme_url") or "-")
        status = str(entry.get("status") or "unknown")
        variant_name = _entry_variant_name(entry, service_name)
        entry_native_target = str(entry.get("selected_native_target") or selected_native_target)
        entry_native_target_dir = _target_display_name(entry_native_target)
        snapshot_path = entry.get("snapshot_path")
        snapshot_text = _read_snapshot_text(
            root,
            snapshot_path if isinstance(snapshot_path, str) else None,
        )

        lines.extend(
            [
                f"### Upstream Entry {index} ({source} / {variant_name})",
                "",
                f"- Upstream native target: `{entry_native_target_dir}`",
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


def _self_maintained_target_readme_markdown(
    target_dir: str,
    service_name: str,
    artifact: TargetArtifact,
    icon_manifest: dict[str, dict[str, Any]] | None = None,
) -> str:
    source_link = None
    if artifact.origin_source_path:
        source_link = os.path.relpath(
            artifact.origin_source_path,
            start=(Path("Rule") / target_dir / service_name).as_posix(),
        )
    lines = [
        f"# {service_name} for {target_dir}",
        "",
        f"This README documents the {target_dir} target derived for {service_name}.",
        "",
        "This directory is self-maintained by egloon_rule_hub.",
        "",
        "- Source type: `self_maintained`",
    ]
    if icon_manifest is not None:
        lines.append(_icon_line(icon_manifest, service_name))
    if artifact.origin_source_path and source_link:
        lines.append(f"- TXT source: [{artifact.origin_source_path}]({source_link})")
    if artifact.origin_source_url:
        lines.append(f"- Source URL: [{artifact.origin_source_url}]({artifact.origin_source_url})")
    lines.extend(
        [
            "",
            "The rules in this directory are generated from the current self-maintained TXT source, not from upstream README manifests.",
            "",
        ]
    )
    return "\n".join(lines)


def _bundle_target_readme_markdown(
    catalog: Catalog,
    bundle_name: str,
    target_name: str,
    target_dir: str,
    target: TargetDef,
    target_artifacts: dict[str, dict[str, TargetArtifact]] | None,
) -> str:
    bundle = catalog.bundles[bundle_name]
    service_names = set(catalog.services)
    bundle_display = _bundle_display_name(bundle_name, service_names)
    bundle_file = _bundle_output_file(
        bundle_name, target_name, target.publish_mode, catalog
    )

    lines = [
        f"# {bundle_display} for {target_dir}",
        "",
        f"This README documents the merged {target_dir} bundle artifact for {bundle_display}.",
        "",
        f"- Bundle file: [{bundle_file}](./{bundle_file})",
        "- Merge strategy: normalized and deduplicated merge of primary published variants only",
        "",
        "## Included Services",
        "",
    ]

    for service_name in bundle.services:
        service_link = f"../{service_name}/README.md"
        primary_variant, extra_variants = _bundle_service_variant_details(
            catalog, service_name, target_name, target_artifacts
        )
        line = (
            f"- {service_name} (primary variant: `{primary_variant}`)"
            f" - [README]({service_link})"
        )
        if extra_variants:
            line += (
                ". Additional manual variants remain available: "
                + ", ".join(f"`{variant_name}`" for variant_name in extra_variants)
            )
        lines.append(line)

    lines.append("")
    return "\n".join(lines)


def _group_manifest_entries_by_service_target(
    manifest: dict[str, list[dict[str, Any]]]
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for service_name, entries in manifest.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            target = entry.get("target")
            if not isinstance(target, str) or not target.strip():
                continue
            service = entry.get("service")
            if not isinstance(service, str) or not service.strip():
                service = service_name
            grouped[(service, target)].append(entry)
    return grouped


def _write_target_readmes_from_artifacts(
    root: Path,
    target_artifacts: dict[str, dict[str, TargetArtifact]],
    manifest: dict[str, list[dict[str, Any]]],
    icon_manifest: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], set[Path]]:
    manifest_by_service_target = _group_manifest_entries_by_service_target(manifest)
    rule_root = root / "Rule"
    service_readme_paths: dict[str, list[str]] = defaultdict(list)
    live_readme_paths: set[Path] = set()

    for service_name, artifacts_by_target in sorted(target_artifacts.items()):
        for target_name, artifact in sorted(artifacts_by_target.items()):
            manifest_entries = manifest_by_service_target.get((service_name, target_name), [])
            target_dir = _target_display_name(target_name)
            if manifest_entries:
                manifest_target_dir = manifest_entries[0].get("target_dir")
                if isinstance(manifest_target_dir, str) and manifest_target_dir.strip():
                    target_dir = manifest_target_dir

            service_dir = rule_root / target_dir / service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            readme_path = service_dir / "README.md"
            if artifact.origin_kind == "self_maintained":
                readme_text = _self_maintained_target_readme_markdown(
                    target_dir, service_name, artifact, icon_manifest
                )
            else:
                readme_text = _target_readme_markdown(
                    root,
                    target_name,
                    target_dir,
                    service_name,
                    manifest_entries,
                    artifact,
                    icon_manifest,
                )
            readme_path.write_text(readme_text, encoding="utf-8")
            live_readme_paths.add(readme_path)
            rel_path = (Path("Rule") / target_dir / service_name / "README.md").as_posix()
            if rel_path not in service_readme_paths[service_name]:
                service_readme_paths[service_name].append(rel_path)

    return dict(service_readme_paths), live_readme_paths


def _self_maintained_target_artifacts_from_catalog(
    catalog: Catalog,
) -> dict[str, dict[str, TargetArtifact]]:
    synthesized: dict[str, dict[str, TargetArtifact]] = {}
    for service_name, service in sorted(catalog.services.items()):
        if service.origin.kind != "self_maintained" or not service.enabled:
            continue
        canonical_rules = catalog.self_maintained_rules.get(service_name)
        if not canonical_rules:
            continue
        artifacts_by_target: dict[str, TargetArtifact] = {}
        for target_name in service.targets:
            target = catalog.targets.get(target_name)
            if target is None or not target.enabled:
                continue
            artifacts_by_target[target_name] = TargetArtifact(
                service=service_name,
                target=target_name,
                selected_family="self_maintained",
                selected_native_target=target_name,
                publish_mode=target.publish_mode,
                is_native=True,
                is_converted=False,
                conversion_path=None,
                origin_kind=service.origin.kind,
                origin_source_path=service.origin.source_path,
                origin_source_url=service.origin.source_url,
                rules=list(canonical_rules),
            )
        if artifacts_by_target:
            synthesized[service_name] = artifacts_by_target
    return synthesized


def _merge_service_readme_paths(
    *path_maps: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = defaultdict(list)
    for path_map in path_maps:
        for service_name, paths in path_map.items():
            for rel_path in paths:
                if rel_path not in merged[service_name]:
                    merged[service_name].append(rel_path)
    return dict(merged)


def _write_target_readmes(
    root: Path,
    manifest: dict[str, list[dict[str, Any]]],
    icon_manifest: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[str]], set[Path]]:
    grouped = _group_manifest_entries_by_target(manifest)
    if not grouped:
        return {}, set()

    rule_root = root / "Rule"
    service_readme_paths: dict[str, list[str]] = defaultdict(list)
    live_readme_paths: set[Path] = set()
    for (target, target_dir, service_name), entries in sorted(grouped.items()):
        service_dir = rule_root / target_dir / service_name
        service_dir.mkdir(parents=True, exist_ok=True)
        readme_path = service_dir / "README.md"
        readme_path.write_text(
            _target_readme_markdown(
                root, target, target_dir, service_name, entries, icon_manifest=icon_manifest
            ),
            encoding="utf-8",
        )
        live_readme_paths.add(readme_path)
        rel_readme = Path("Rule") / target_dir / service_name / "README.md"
        rel_path = rel_readme.as_posix()
        if rel_path not in service_readme_paths[service_name]:
            service_readme_paths[service_name].append(rel_path)

    return dict(service_readme_paths), live_readme_paths


def _prune_stale_target_readmes(root: Path, live_readme_paths: set[Path]) -> None:
    rule_root = root / "Rule"
    if not rule_root.exists():
        return

    for readme_path in sorted(rule_root.rglob("README.md")):
        try:
            rel_parts = readme_path.relative_to(rule_root).parts
        except ValueError:
            continue
        if len(rel_parts) != 3:
            continue
        if readme_path not in live_readme_paths:
            readme_path.unlink()

    for path in sorted(rule_root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _write_bundle_readmes(
    root: Path,
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]] | None,
) -> set[Path]:
    rule_root = root / "Rule"
    live_readme_paths: set[Path] = set()

    for bundle_name, bundle in sorted(catalog.bundles.items()):
        if not bundle.enabled:
            continue
        bundle_display = _bundle_display_name(bundle_name, set(catalog.services))
        for target_name in bundle.targets:
            target = catalog.targets.get(target_name)
            if target is None or not target.enabled:
                continue
            target_dir = _target_display_name(target_name)
            bundle_dir = rule_root / target_dir / bundle_display
            bundle_file = bundle_dir / _bundle_output_file(
                bundle_name, target_name, target.publish_mode, catalog
            )
            if not bundle_file.exists():
                continue
            bundle_dir.mkdir(parents=True, exist_ok=True)
            readme_path = bundle_dir / "README.md"
            readme_path.write_text(
                _bundle_target_readme_markdown(
                    catalog,
                    bundle_name,
                    target_name,
                    target_dir,
                    target,
                    target_artifacts,
                ),
                encoding="utf-8",
            )
            live_readme_paths.add(readme_path)

    return live_readme_paths


def write_markdown_docs(
    root: Path,
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]] | None = None,
) -> None:
    docs_dir = root / "docs"
    legacy_services_dir = docs_dir / "services"
    if legacy_services_dir.exists():
        if legacy_services_dir.is_dir():
            shutil.rmtree(legacy_services_dir)
        else:
            legacy_services_dir.unlink()
    upstream_docs_manifest = _load_upstream_docs_manifest(root)
    icons_manifest = _load_icons_manifest(root)

    if target_artifacts is None:
        service_readme_paths, live_readme_paths = _write_target_readmes(
            root, upstream_docs_manifest, icons_manifest
        )
        self_maintained_artifacts = _self_maintained_target_artifacts_from_catalog(catalog)
        if self_maintained_artifacts:
            (
                self_maintained_readme_paths,
                self_maintained_live_paths,
            ) = _write_target_readmes_from_artifacts(
                root, self_maintained_artifacts, upstream_docs_manifest, icons_manifest
            )
            service_readme_paths = _merge_service_readme_paths(
                service_readme_paths, self_maintained_readme_paths
            )
            live_readme_paths |= self_maintained_live_paths
    else:
        service_readme_paths, live_readme_paths = _write_target_readmes_from_artifacts(
            root, target_artifacts, upstream_docs_manifest, icons_manifest
        )
    live_readme_paths |= _write_bundle_readmes(root, catalog, target_artifacts)
    _prune_stale_target_readmes(root, live_readme_paths)
    for legacy_path in (
        docs_dir / "services.md",
        docs_dir / "sources.md",
        docs_dir / "usage.md",
        docs_dir / "attribution.md",
    ):
        if legacy_path.exists():
            legacy_path.unlink()
    if docs_dir.exists():
        for path in sorted(docs_dir.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    (root / "ATTRIBUTION.md").write_text(_attribution_markdown(catalog), encoding="utf-8")
