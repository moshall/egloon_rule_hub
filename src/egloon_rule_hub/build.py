from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen
import shutil

import yaml

from egloon_rule_hub.emitters.clash import render_clash_rule_provider
from egloon_rule_hub.emitters.egern import render_egern_rule_set
from egloon_rule_hub.emitters.loon import render_loon_rules
from egloon_rule_hub.emitters.loon_lsr import render_loon_lsr
from egloon_rule_hub.emitters.quanx import render_quanx_rules
from egloon_rule_hub.emitters.shadowrocket import render_shadowrocket_rules
from egloon_rule_hub.model.catalog import Catalog, ServiceDef, SourceRef, TargetDef
from egloon_rule_hub.model.publish import SelectedSourceEntry, TargetArtifact
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
    "quanx": ("list", render_quanx_rules),
    "shadowrocket": ("list", render_shadowrocket_rules),
}


TARGET_DISPLAY_NAMES = {
    "egern": "Egern",
    "loon": "Loon",
    "clash": "Clash",
    "quanx": "QuanX",
    "shadowrocket": "Shadowrocket",
}


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "egloon-rule-hub/0.1"})
    with urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


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
    catalog: Catalog, service: ServiceDef, target_name: str
) -> tuple[str, list[SourceRef]]:
    target_config = service.target_sources.get(target_name)
    if target_config is None:
        return "", []

    for family in target_config.selected_order(
        service.fallback_order, catalog.default_fallback_order
    ):
        candidates = target_config.families.get(family, [])
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
        )

    family, source_refs = _selected_family_sources(catalog, service, target_name)
    if not family or not source_refs:
        return None

    streams: list[list[Rule]] = []
    selected_entries: list[SelectedSourceEntry] = []
    for source_ref in sorted(source_refs, key=lambda item: item.priority, reverse=True):
        source_def = catalog.sources[source_ref.source]
        resolved = resolve_source_ref(source_def, source_ref)
        parser = FORMAT_PARSERS.get(resolved.format or "")
        if parser is None:
            raise ValueError(
                f"Unsupported source format for {service_name}/{target_name}: {resolved.format!r}"
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

    return TargetArtifact(
        service=service_name,
        target=target_name,
        selected_family=family,
        selected_native_target=selected_native_target,
        publish_mode=target.publish_mode,
        is_native=is_native,
        is_converted=not is_native,
        conversion_path=conversion_path,
        origin_kind=service.origin.kind,
        origin_source_path=service.origin.source_path,
        origin_source_url=service.origin.source_url,
        rules=merged,
        selected_entries=selected_entries,
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
    _prune_legacy_dist_targets(dist_dir, catalog.targets)
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

    for bundle_name, bundle in catalog.bundles.items():
        if not bundle.enabled:
            continue
        merged = merge_rule_streams(
            [service_rules.get(service_name, []) for service_name in bundle.services]
        )
        if not merged:
            continue
        bundle_dir = dist_dir / "bundles" / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        for target_name in bundle.targets:
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            if target is None or not target.enabled or renderer_info is None:
                continue
            ext = _target_output_ext(target_name, target)
            output_path = bundle_dir / f"{target_name}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(bundle_name, target_name, target, merged),
                encoding="utf-8",
            )


def render_target_artifacts(
    root: Path,
    catalog: Catalog,
    target_artifacts: dict[str, dict[str, TargetArtifact]],
) -> None:
    dist_dir = root / "dist"
    _prune_legacy_dist_targets(dist_dir, catalog.targets)
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
            output_path = service_dir / f"{service_name}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(
                    service_name,
                    target_name,
                    target,
                    artifact.rules,
                    [entry.raw_text for entry in artifact.selected_entries],
                ),
                encoding="utf-8",
            )

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
            base_output_path = service_dir / f"{service_name}.{_target_output_ext(target_name, target)}"
            for ext in _target_output_ext_candidates(target_name, target):
                candidate = base_output_path.with_suffix(f".{ext}")
                if candidate.exists() and candidate.is_file():
                    candidate.unlink()

    for bundle_name, bundle in catalog.bundles.items():
        if not bundle.enabled:
            continue
        bundle_dir = dist_dir / "bundles" / bundle_name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        for target_name in bundle.targets:
            merged = merge_rule_streams(
                [
                    target_artifacts.get(service_name, {})
                    .get(target_name, TargetArtifact(
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
                    ))
                    .rules
                    for service_name in bundle.services
                ]
            )
            if not merged:
                continue
            target = catalog.targets.get(target_name)
            renderer_info = TARGET_RENDERERS.get(target_name)
            if target is None or not target.enabled or renderer_info is None:
                continue
            ext = _target_output_ext(target_name, target)
            output_path = bundle_dir / f"{target_name}.{ext}"
            _prune_stale_output_variants(output_path, target_name, target)
            output_path.write_text(
                _render_target_output(bundle_name, target_name, target, merged),
                encoding="utf-8",
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
