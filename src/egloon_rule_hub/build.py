from __future__ import annotations

import json
from pathlib import Path
from pathlib import PurePosixPath
from urllib.request import Request, urlopen
import re
import shutil

import yaml

from egloon_rule_hub.emitters.clash import render_clash_rule_provider
from egloon_rule_hub.emitters.egern import render_egern_rule_set
from egloon_rule_hub.emitters.loon import render_loon_rules
from egloon_rule_hub.emitters.loon_lsr import render_loon_lsr
from egloon_rule_hub.emitters.quanx import render_quanx_rules
from egloon_rule_hub.emitters.shadowrocket import render_shadowrocket_rules
from egloon_rule_hub.model.catalog import Catalog, ServiceDef, ServiceTargetVariantDef, SourceRef, TargetDef
from egloon_rule_hub.model.publish import SelectedSourceEntry, TargetArtifact, TargetArtifactVariant
from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.normalize.dedupe import dedupe_rules
from egloon_rule_hub.normalize.merge import merge_rule_streams
from egloon_rule_hub.parsers.clash import parse_clash_rule_provider
from egloon_rule_hub.parsers.egern import parse_egern_rule_set
from egloon_rule_hub.parsers.loon import parse_loon_list
from egloon_rule_hub.parsers.quanx import parse_quanx_list
from egloon_rule_hub.parsers.shadowrocket import parse_shadowrocket_list
from egloon_rule_hub.sources.registry import resolve_source_ref

FORMAT_PARSERS = {
    "clash_yaml": parse_clash_rule_provider,
    "clash_list": parse_loon_list,
    "egern_yaml": parse_egern_rule_set,
    "loon_list": parse_loon_list,
    "quanx_list": parse_quanx_list,
    "shadowrocket_list": parse_shadowrocket_list,
}

TARGET_RENDERERS = {
    "egern": ("yaml", render_egern_rule_set),
    "loon": ("list", render_loon_rules),
    "clash": ("yaml", render_clash_rule_provider),
    "quantumultx": ("list", render_quanx_rules),
    "shadowrocket": ("list", render_shadowrocket_rules),
}

GITHUB_TREE_SOURCE_KINDS = frozenset(
    {"github_repo", "blackmatrix7_repo", "acl4ssr_repo", "shadowrocket_repo"}
)


TARGET_DISPLAY_NAMES = {
    "egern": "Egern",
    "loon": "Loon",
    "clash": "Clash",
    "quantumultx": "QuantumultX",
    "shadowrocket": "Shadowrocket",
}

BUNDLE_DISPLAY_NAMES = {
    "ai": "AI",
}

_REPO_TREE_CACHE: dict[tuple[str, str], list[str]] = {}


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "egloon-rule-hub/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


def _fetch_repo_tree(source_def: SourceDef) -> list[str]:
    if not source_def.repo or not source_def.branch:
        return []
    cache_key = (source_def.repo, source_def.branch)
    cached = _REPO_TREE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    api_url = (
        f"https://api.github.com/repos/{source_def.repo}/git/trees/"
        f"{source_def.branch}?recursive=1"
    )
    request = Request(api_url, headers={"User-Agent": "egloon-rule-hub/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    tree = payload.get("tree", [])
    repo_paths = [
        str(item.get("path"))
        for item in tree
        if item.get("type") == "blob" and isinstance(item.get("path"), str)
    ]
    _REPO_TREE_CACHE[cache_key] = repo_paths
    return repo_paths


def _discover_source_ref_variants(
    service_name: str,
    source_def: SourceDef,
    source_ref: SourceRef,
    repo_paths: list[str],
) -> dict[str, SourceRef]:
    if source_def.kind not in GITHUB_TREE_SOURCE_KINDS or not source_ref.path:
        return {service_name: source_ref}

    base_path = PurePosixPath(source_ref.path)
    base_dir = str(base_path.parent)
    base_suffix = base_path.suffix
    service_pattern = re.compile(rf"^{re.escape(service_name)}(?:[_.-].+)?$")

    matches: list[str] = []
    for repo_path in repo_paths:
        repo_file = PurePosixPath(repo_path)
        if str(repo_file.parent) != base_dir:
            continue
        if repo_file.suffix != base_suffix:
            continue
        if not service_pattern.fullmatch(repo_file.stem):
            continue
        matches.append(repo_path)

    if not matches:
        return {service_name: source_ref}

    discovered: dict[str, SourceRef] = {}
    for repo_path in sorted(matches, key=lambda value: (PurePosixPath(value).stem != service_name, value)):
        variant_name = PurePosixPath(repo_path).stem
        discovered[variant_name] = SourceRef(
            source=source_ref.source,
            path=repo_path,
            url=source_ref.url,
            format=source_ref.format,
            priority=source_ref.priority,
        )
    return discovered


def _auto_discovered_target_variants(
    catalog: Catalog,
    service: ServiceDef,
    target_name: str,
    target_config: ServiceTargetDef,
    repo_tree_fetcher=_fetch_repo_tree,
) -> dict[str, ServiceTargetVariantDef]:
    if target_config.variants:
        return target_config.normalized_variants(service.name)

    default_variant = target_config.normalized_variants(service.name)[service.name]
    selected_family, family_sources = _selected_family_sources(
        catalog,
        service,
        target_name,
        default_variant,
        target_config.fallback_order,
    )
    if not selected_family or not family_sources:
        return target_config.normalized_variants(service.name)

    variant_sources: dict[str, list[SourceRef]] = {}
    for source_ref in sorted(family_sources, key=lambda item: item.priority, reverse=True):
        source_def = catalog.sources[source_ref.source]
        repo_paths = repo_tree_fetcher(source_def)
        discovered = _discover_source_ref_variants(
            service.name,
            source_def,
            source_ref,
            repo_paths,
        )
        for variant_name, variant_source_ref in discovered.items():
            variant_sources.setdefault(variant_name, []).append(variant_source_ref)

    if len(variant_sources) <= 1:
        return target_config.normalized_variants(service.name)

    primary_variant_name = (
        service.name if service.name in variant_sources else sorted(variant_sources)[0]
    )
    ordered_variant_names = [
        primary_variant_name,
        *sorted(name for name in variant_sources if name != primary_variant_name),
    ]
    return {
        variant_name: ServiceTargetVariantDef(
            name=variant_name,
            primary=variant_name == primary_variant_name,
            families={selected_family: list(variant_sources[variant_name])},
            fallback_order=[selected_family],
        )
        for variant_name in ordered_variant_names
    }


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


def _load_override(root: Path, override_path: str | None) -> dict:
    if not override_path:
        return {}
    path = root / override_path
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _apply_override(root: Path, rules: list[Rule], override_path: str | None) -> list[Rule]:
    override = _load_override(root, override_path)
    remove_items = {
        (str(item["type"]).upper(), str(item["value"]))
        for item in override.get("remove", [])
    }
    disable_items = {
        (str(item["type"]).upper(), str(item["value"]))
        for item in override.get("disable", [])
    }
    filtered = [
        rule
        for rule in rules
        if (rule.type, rule.value) not in remove_items
        and (rule.type, rule.value) not in disable_items
    ]
    appended = [
        Rule(str(item["type"]).upper(), str(item["value"]))
        for item in override.get("append", [])
    ]
    return dedupe_rules(filtered + appended)


def build_service_rules(
    catalog: Catalog,
    service_name: str,
    fetcher=fetch_text,
) -> list[Rule]:
    service = catalog.services[service_name]
    streams: list[list[Rule]] = []

    for source_ref in sorted(service.sources, key=lambda item: item.priority, reverse=True):
        source_def = catalog.sources[source_ref.source]
        resolved = resolve_source_ref(source_def, source_ref)
        parser = FORMAT_PARSERS.get(resolved.format or "")
        if parser is None:
            raise ValueError(
                f"Unsupported source format for {service_name}: {resolved.format!r}"
            )
        content = fetcher(resolved.url)
        streams.append(parser(content))

    merged = merge_rule_streams(streams)
    return _apply_override(catalog.root, merged, service.override)


def build_all_service_rules(catalog: Catalog, fetcher=fetch_text) -> dict[str, list[Rule]]:
    built: dict[str, list[Rule]] = {}
    for service_name, service in catalog.services.items():
        if not service.enabled:
            continue
        if not service.sources:
            continue
        built[service_name] = build_service_rules(catalog, service_name, fetcher=fetcher)
    return built


def _selected_family_sources(
    catalog: Catalog,
    service: ServiceDef,
    target_name: str,
    variant_def: ServiceTargetVariantDef,
    target_fallback_order: list[str],
) -> tuple[str, list[SourceRef]]:
    for family in variant_def.selected_order(
        target_fallback_order,
        service.fallback_order,
        catalog.default_fallback_order,
    ):
        candidates = variant_def.families.get(family, [])
        if candidates:
            return family, candidates
    return "", []


def _family_native_target(target_name: str, family: str) -> str:
    if family == "native":
        return target_name
    return family


def build_target_artifact(
    catalog: Catalog,
    service_name: str,
    target_name: str,
    fetcher=fetch_text,
) -> TargetArtifact | None:
    service = catalog.services[service_name]
    target = catalog.targets.get(target_name)
    if target is None or not target.enabled:
        return None

    if service.origin.kind == "self_maintained":
        canonical_rules = catalog.self_maintained_rules.get(service_name)
        if not canonical_rules:
            return None
        return TargetArtifact(
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
            selected_entries=[],
            primary_variant_name=service_name,
        )

    target_config = service.target_sources.get(target_name)
    if target_config is None:
        return None

    variant_defs = _auto_discovered_target_variants(
        catalog,
        service,
        target_name,
        target_config,
    )

    variants: dict[str, TargetArtifactVariant] = {}
    primary_variant_name: str | None = None
    for variant_name, variant_def in variant_defs.items():
        family, source_refs = _selected_family_sources(
            catalog,
            service,
            target_name,
            variant_def,
            target_config.fallback_order,
        )
        if not family or not source_refs:
            continue

        streams: list[list[Rule]] = []
        selected_entries: list[SelectedSourceEntry] = []
        for source_ref in sorted(source_refs, key=lambda item: item.priority, reverse=True):
            source_def = catalog.sources[source_ref.source]
            resolved = resolve_source_ref(source_def, source_ref)
            parser = FORMAT_PARSERS.get(resolved.format or "")
            if parser is None:
                raise ValueError(
                    f"Unsupported source format for {service_name}/{target_name}/{variant_name}: {resolved.format!r}"
                )
            raw_text = fetcher(resolved.url)
            streams.append(parser(raw_text))
            selected_entries.append(
                SelectedSourceEntry(
                    source_name=resolved.source_name,
                    family=family,
                    format=resolved.format,
                    url=resolved.url,
                    priority=resolved.priority,
                    raw_text=raw_text,
                )
            )

        merged = merge_rule_streams(streams)
        merged = _apply_override(catalog.root, merged, service.override)
        selected_native_target = _family_native_target(target_name, family)
        is_native = family == "native"
        conversion_path = None
        if not is_native:
            conversion_path = (
                f"{TARGET_DISPLAY_NAMES.get(selected_native_target, selected_native_target.capitalize())}"
                f" -> {TARGET_DISPLAY_NAMES.get(target_name, target_name.capitalize())}"
            )

        variants[variant_name] = TargetArtifactVariant(
            name=variant_name,
            primary=variant_def.primary,
            selected_family=family,
            selected_native_target=selected_native_target,
            publish_mode=target.publish_mode,
            is_native=is_native,
            is_converted=not is_native,
            conversion_path=conversion_path,
            rules=merged,
            selected_entries=selected_entries,
        )
        if variant_def.primary:
            primary_variant_name = variant_name

    if not variants or primary_variant_name is None or primary_variant_name not in variants:
        return None

    primary_variant = variants[primary_variant_name]
    return TargetArtifact(
        service=service_name,
        target=target_name,
        selected_family=primary_variant.selected_family,
        selected_native_target=primary_variant.selected_native_target,
        publish_mode=primary_variant.publish_mode,
        is_native=primary_variant.is_native,
        is_converted=primary_variant.is_converted,
        conversion_path=primary_variant.conversion_path,
        origin_kind=service.origin.kind,
        origin_source_path=service.origin.source_path,
        origin_source_url=service.origin.source_url,
        rules=list(primary_variant.rules),
        selected_entries=list(primary_variant.selected_entries),
        primary_variant_name=primary_variant_name,
        variants=variants,
    )


def build_all_target_artifacts(
    catalog: Catalog, fetcher=fetch_text
) -> dict[str, dict[str, TargetArtifact]]:
    built: dict[str, dict[str, TargetArtifact]] = {}
    for service_name, service in catalog.services.items():
        if not service.enabled:
            continue
        target_artifacts: dict[str, TargetArtifact] = {}
        for target_name in service.targets:
            artifact = build_target_artifact(
                catalog, service_name, target_name, fetcher=fetcher
            )
            if artifact is not None:
                target_artifacts[target_name] = artifact
        if target_artifacts:
            built[service_name] = target_artifacts
    return built


def _target_output_ext(target_name: str, target: TargetDef | None) -> str:
    if target_name == "loon" and target is not None and target.publish_mode == "lsr":
        return "lsr"
    renderer_info = TARGET_RENDERERS.get(target_name)
    if renderer_info is None:
        raise ValueError(f"Unsupported target renderer for {target_name!r}")
    return renderer_info[0]


def _target_output_ext_candidates(target_name: str, target: TargetDef | None) -> set[str]:
    candidates = {_target_output_ext(target_name, target)}
    renderer_info = TARGET_RENDERERS.get(target_name)
    if renderer_info is not None:
        candidates.add(renderer_info[0])
    if target is not None and target.file_ext:
        candidates.add(target.file_ext)
    return {candidate for candidate in candidates if candidate}


def _prune_stale_output_variants(output_path: Path, target_name: str, target: TargetDef | None) -> None:
    for ext in _target_output_ext_candidates(target_name, target):
        candidate = output_path.with_suffix(f".{ext}")
        if candidate == output_path or not candidate.exists():
            continue
        if candidate.is_file():
            candidate.unlink()


def _prune_stale_service_variant_outputs(
    service_dir: Path,
    live_basenames: set[str],
    target_name: str,
    target: TargetDef | None,
) -> None:
    if not service_dir.exists():
        return
    for ext in _target_output_ext_candidates(target_name, target):
        for candidate in service_dir.glob(f"*.{ext}"):
            if candidate.stem in live_basenames or candidate.name == "README.md":
                continue
            if candidate.is_file():
                candidate.unlink()


def _prune_legacy_bundle_outputs(dist_dir: Path) -> None:
    legacy_bundle_dir = dist_dir / "bundles"
    if not legacy_bundle_dir.exists():
        return
    if legacy_bundle_dir.is_dir():
        shutil.rmtree(legacy_bundle_dir)
    else:
        legacy_bundle_dir.unlink()


def _render_target_output(
    service_name: str,
    target_name: str,
    target: TargetDef | None,
    rules: list[Rule],
    source_texts: list[str] | None = None,
) -> str:
    if target_name == "loon" and target is not None and target.publish_mode == "lsr":
        return render_loon_lsr(service_name, rules, source_texts or [])
    renderer_info = TARGET_RENDERERS.get(target_name)
    if renderer_info is None:
        raise ValueError(f"Unsupported target renderer for {target_name!r}")
    return renderer_info[1](rules)


def render_rule_artifacts(
    root: Path,
    catalog: Catalog,
    service_rules: dict[str, list[Rule]],
) -> None:
    dist_dir = root / "dist"
    _prune_legacy_rule_targets(root / "Rule", catalog.targets)
    _prune_legacy_dist_targets(dist_dir, catalog.targets)
    _prune_legacy_bundle_outputs(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    for service_name, rules in service_rules.items():
        if not rules:
            continue
        service = catalog.services[service_name]
        for target_name in service.targets:
            display_target = TARGET_DISPLAY_NAMES.get(target_name)
            if display_target is None:
                raise ValueError(
                    f"Target {target_name!r} lacks a display name required to publish service {service_name!r}"
                )
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            if target is None or not target.enabled or renderer_info is None:
                continue
            ext = _target_output_ext(target_name, target)
            service_dir = root / "Rule" / display_target / service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            output_path = service_dir / f"{service_name}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(service_name, target_name, target, rules),
                encoding="utf-8",
            )

    service_names = set(catalog.services)
    for bundle_name, bundle in catalog.bundles.items():
        if not bundle.enabled:
            continue
        bundle_display = _bundle_display_name(bundle_name, service_names)
        for target_name in bundle.targets:
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            display_target = TARGET_DISPLAY_NAMES.get(target_name)
            if (
                target is None
                or not target.enabled
                or renderer_info is None
                or display_target is None
            ):
                continue
            bundle_dir = root / "Rule" / display_target / bundle_display
            merged = merge_rule_streams(
                [service_rules.get(service_name, []) for service_name in bundle.services]
            )
            if not merged:
                _prune_stale_service_variant_outputs(bundle_dir, set(), target_name, target)
                continue
            bundle_dir.mkdir(parents=True, exist_ok=True)
            ext = _target_output_ext(target_name, target)
            output_path = bundle_dir / f"{bundle_display}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(bundle_display, target_name, target, merged),
                encoding="utf-8",
            )
            _prune_stale_service_variant_outputs(
                bundle_dir, {bundle_display}, target_name, target
            )


def render_target_artifacts(
    root: Path,
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]],
) -> None:
    dist_dir = root / "dist"
    _prune_legacy_rule_targets(root / "Rule", catalog.targets)
    _prune_legacy_dist_targets(dist_dir, catalog.targets)
    _prune_legacy_bundle_outputs(dist_dir)
    dist_dir.mkdir(parents=True, exist_ok=True)

    for service_name, service_targets in target_artifacts.items():
        for target_name, artifact in service_targets.items():
            display_target = TARGET_DISPLAY_NAMES.get(target_name)
            if display_target is None:
                raise ValueError(
                    f"Target {target_name!r} lacks a display name required to publish service {service_name!r}"
                )
            renderer_info = TARGET_RENDERERS.get(target_name)
            target = catalog.targets.get(target_name)
            if target is None or not target.enabled or renderer_info is None:
                continue
            ext = _target_output_ext(target_name, target)
            service_dir = root / "Rule" / display_target / service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            live_basenames: set[str] = set()
            for variant_name, variant in artifact.variants.items():
                output_path = service_dir / f"{variant_name}.{ext}"
                live_basenames.add(variant_name)
                _prune_stale_output_variants(output_path, target_name, target)
                output_path.write_text(
                    _render_target_output(
                        variant_name,
                        target_name,
                        target,
                        variant.rules,
                        [entry.raw_text for entry in variant.selected_entries],
                    ),
                    encoding="utf-8",
                )
            _prune_stale_service_variant_outputs(service_dir, live_basenames, target_name, target)

    for service_name, service in catalog.services.items():
        service_targets = target_artifacts.get(service_name, {})
        for target_name in service.targets:
            if target_name in service_targets:
                continue
            display_target = TARGET_DISPLAY_NAMES.get(target_name)
            if display_target is None:
                continue
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            if target is None or not target.enabled or renderer_info is None:
                continue
            service_dir = root / "Rule" / display_target / service_name
            if not service_dir.exists():
                continue
            _prune_stale_service_variant_outputs(service_dir, set(), target_name, target)

    service_names = set(catalog.services)
    for bundle_name, bundle in catalog.bundles.items():
        if not bundle.enabled:
            continue
        bundle_display = _bundle_display_name(bundle_name, service_names)
        for target_name in bundle.targets:
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            display_target = TARGET_DISPLAY_NAMES.get(target_name)
            if (
                target is None
                or not target.enabled
                or renderer_info is None
                or display_target is None
            ):
                continue
            bundle_dir = root / "Rule" / display_target / bundle_display
            merged = merge_rule_streams(
                [
                    target_artifacts.get(service_name, {})
                    .get(
                        target_name,
                        TargetArtifact(
                            service=service_name,
                            target=target_name,
                            selected_family="",
                            selected_native_target=target_name,
                            publish_mode=None,
                            is_native=False,
                            is_converted=False,
                            conversion_path=None,
                            rules=[],
                            selected_entries=[],
                        ),
                    )
                    .rules
                    for service_name in bundle.services
                ]
            )
            if not merged:
                _prune_stale_service_variant_outputs(bundle_dir, set(), target_name, target)
                continue
            bundle_dir.mkdir(parents=True, exist_ok=True)
            ext = _target_output_ext(target_name, target)
            output_path = bundle_dir / f"{bundle_display}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(bundle_display, target_name, target, merged),
                encoding="utf-8",
            )
            _prune_stale_service_variant_outputs(
                bundle_dir, {bundle_display}, target_name, target
            )


def _prune_legacy_dist_targets(
    dist_dir: Path, targets: dict[str, TargetDef]
) -> None:
    if not dist_dir.exists():
        return
    for target_name in targets:
        legacy_dir = dist_dir / target_name
        if not legacy_dir.exists():
            continue
        if legacy_dir.is_dir():
            shutil.rmtree(legacy_dir)
        else:
            legacy_dir.unlink()


def _prune_legacy_rule_targets(
    rule_root: Path, targets: dict[str, TargetDef]
) -> None:
    if not rule_root.exists():
        return
    live_target_dirs = {
        TARGET_DISPLAY_NAMES.get(target_name, target_name.capitalize())
        for target_name in targets
    }
    for legacy_name in ("QuanX",):
        legacy_dir = rule_root / legacy_name
        if legacy_name in live_target_dirs or not legacy_dir.exists():
            continue
        if legacy_dir.is_dir():
            shutil.rmtree(legacy_dir)
        else:
            legacy_dir.unlink()
