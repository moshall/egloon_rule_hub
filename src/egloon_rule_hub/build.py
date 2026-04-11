from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

import yaml

from egloon_rule_hub.emitters.clash import render_clash_rule_provider
from egloon_rule_hub.emitters.egern import render_egern_rule_set
from egloon_rule_hub.emitters.loon import render_loon_rules
from egloon_rule_hub.emitters.quanx import render_quanx_rules
from egloon_rule_hub.emitters.shadowrocket import render_shadowrocket_rules
from egloon_rule_hub.model.catalog import Catalog
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


def render_rule_artifacts(
    root: Path,
    catalog: Catalog,
    service_rules: dict[str, list[Rule]],
) -> None:
    dist_dir = root / "dist"
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
            ext, renderer = renderer_info
            service_dir = root / "Rule" / display_target / service_name
            service_dir.mkdir(parents=True, exist_ok=True)
            output_path = service_dir / f"{service_name}.{ext}"
            output_path.write_text(renderer(rules), encoding="utf-8")

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
            ext, renderer = renderer_info
            output_path = bundle_dir / f"{target_name}.{ext}"
            output_path.write_text(renderer(merged), encoding="utf-8")
