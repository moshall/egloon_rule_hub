from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from egloon_rule_hub.model.rules import Rule
from egloon_rule_hub.txt_sources import discover_txt_services

DEFAULT_FALLBACK_ORDER = ["native", "shadowrocket", "clash"]
ALLOWED_SOURCE_FAMILIES = frozenset(DEFAULT_FALLBACK_ORDER)
DEFAULT_TXT_TARGETS = [
    "egern",
    "loon",
    "clash",
    "quantumultx",
    "shadowrocket",
    "surfboard",
    "singbox",
]


@dataclass(slots=True)
class SourceDef:
    name: str
    kind: str
    repo: str | None = None
    branch: str | None = None
    base_raw_url: str | None = None


@dataclass(slots=True)
class SourceRef:
    source: str
    path: str | None = None
    url: str | None = None
    format: str | None = None
    priority: int = 100


@dataclass(slots=True)
class ServiceTargetVariantDef:
    name: str
    primary: bool
    families: dict[str, list[SourceRef]] = field(default_factory=dict)
    fallback_order: list[str] = field(default_factory=list)

    def selected_order(self, target_fallback_order: list[str], service_fallback_order: list[str], default_order: list[str]) -> list[str]:
        if self.fallback_order:
            return self.fallback_order
        if target_fallback_order:
            return target_fallback_order
        if service_fallback_order:
            return service_fallback_order
        return default_order


@dataclass(slots=True)
class ServiceTargetDef:
    name: str
    families: dict[str, list[SourceRef]] = field(default_factory=dict)
    variants: dict[str, ServiceTargetVariantDef] = field(default_factory=dict)
    fallback_order: list[str] = field(default_factory=list)

    def selected_order(self, service_fallback_order: list[str], default_order: list[str]) -> list[str]:
        if self.fallback_order:
            return self.fallback_order
        if service_fallback_order:
            return service_fallback_order
        return default_order

    def normalized_variants(self, service_name: str) -> dict[str, ServiceTargetVariantDef]:
        if self.variants:
            return self.variants
        return {
            service_name: ServiceTargetVariantDef(
                name=service_name,
                primary=True,
                families=self.families,
                fallback_order=self.fallback_order,
            )
        }


@dataclass(slots=True)
class ServiceOrigin:
    kind: str = "upstream"
    source_path: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    generated_by: str | None = None


@dataclass(slots=True)
class ServiceDef:
    name: str
    enabled: bool
    targets: list[str]
    sources: list[SourceRef] = field(default_factory=list)
    target_sources: dict[str, ServiceTargetDef] = field(default_factory=dict)
    fallback_order: list[str] = field(default_factory=list)
    override: str | None = None
    notes: str = ""
    origin: ServiceOrigin = field(default_factory=ServiceOrigin)

    @property
    def outputs(self) -> list[str]:
        return self.targets


@dataclass(slots=True)
class BundleDef:
    name: str
    enabled: bool
    targets: list[str]
    services: list[str]


@dataclass(slots=True)
class TargetDef:
    name: str
    enabled: bool
    file_ext: str
    publish_mode: str | None = None
    source_target: str | None = None


@dataclass(slots=True)
class Catalog:
    root: Path
    sources: dict[str, SourceDef]
    targets: dict[str, TargetDef]
    services: dict[str, ServiceDef]
    bundles: dict[str, BundleDef]
    default_fallback_order: list[str] = field(default_factory=lambda: DEFAULT_FALLBACK_ORDER.copy())
    self_maintained_rules: dict[str, list[Rule]] = field(default_factory=dict)
    self_maintained_failures: dict[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        known_targets = set(self.targets)
        known_sources = set(self.sources)

        for target in self.targets.values():
            if target.source_target is None:
                continue
            if target.source_target not in known_targets:
                raise ValueError(
                    f"Target {target.name} references unknown source_target: {target.source_target}"
                )
            visited = {target.name}
            source_target = target.source_target
            while source_target is not None:
                if source_target in visited:
                    raise ValueError(
                        f"Target {target.name} has a circular source_target chain"
                    )
                visited.add(source_target)
                source_target = self.targets[source_target].source_target

        for service in self.services.values():
            unknown_targets = sorted(set(service.targets) - known_targets)
            if unknown_targets:
                raise ValueError(
                    f"Service {service.name} references unknown targets: {unknown_targets}"
                )
            unknown_service_families = sorted(
                family
                for family in service.fallback_order
                if family not in ALLOWED_SOURCE_FAMILIES
            )
            if unknown_service_families:
                raise ValueError(
                    f"Service {service.name} has unknown fallback families: {unknown_service_families}"
                )

            for target_name, target_def in service.target_sources.items():
                if target_name not in known_targets:
                    raise ValueError(
                        f"Service {service.name} target_sources references unknown target: {target_name}"
                    )
                unknown_target_families = sorted(
                    family
                    for family in target_def.fallback_order
                    if family not in ALLOWED_SOURCE_FAMILIES
                )
                if unknown_target_families:
                    raise ValueError(
                        f"Service {service.name} target {target_name} has unknown fallback order families: {unknown_target_families}"
                    )
                variants = target_def.normalized_variants(service.name)
                primary_variants = [variant.name for variant in variants.values() if variant.primary]
                if len(primary_variants) != 1:
                    raise ValueError(
                        f"Service {service.name} target {target_name} must define exactly one primary variant"
                    )
                for variant in variants.values():
                    unknown_families = sorted(
                        family for family in variant.families if family not in ALLOWED_SOURCE_FAMILIES
                    )
                    if unknown_families:
                        raise ValueError(
                            f"Service {service.name} target {target_name} variant {variant.name} has unknown families: {unknown_families}"
                        )
                    unknown_variant_families = sorted(
                        family
                        for family in variant.fallback_order
                        if family not in ALLOWED_SOURCE_FAMILIES
                    )
                    if unknown_variant_families:
                        raise ValueError(
                            f"Service {service.name} target {target_name} variant {variant.name} has unknown fallback order families: {unknown_variant_families}"
                        )

            for source_ref in service.sources:
                if source_ref.source not in known_sources:
                    raise ValueError(
                        f"Service {service.name} references unknown source:"
                        f" {source_ref.source}"
                    )
                if not source_ref.path and not source_ref.url:
                    raise ValueError(
                        f"Service {service.name} source {source_ref.source}"
                        " must define path or url"
                    )

        for bundle in self.bundles.values():
            unknown_targets = sorted(set(bundle.targets) - known_targets)
            if unknown_targets:
                raise ValueError(
                    f"Bundle {bundle.name} references unknown targets: {unknown_targets}"
                )
            unknown_services = sorted(set(bundle.services) - set(self.services))
            if unknown_services:
                raise ValueError(
                    f"Bundle {bundle.name} references unknown services: {unknown_services}"
                )


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def _relative_catalog_path(root: Path, source_path: Path) -> str:
    try:
        return source_path.relative_to(root).as_posix()
    except ValueError:
        return str(source_path)


def load_catalog(root: Path) -> Catalog:
    catalog_dir = root / "catalog"
    sources_doc = _load_yaml(catalog_dir / "sources.yaml").get("sources", {})
    targets_doc = _load_yaml(catalog_dir / "targets.yaml").get("targets", {})
    services_payload = _load_yaml(catalog_dir / "services.yaml")
    services_doc = services_payload.get("services", {})
    bundles_doc = _load_yaml(catalog_dir / "bundles.yaml").get("bundles", {})
    defaults_doc = services_payload.get("defaults", {})

    sources = {
        name: SourceDef(name=name, **payload) for name, payload in sources_doc.items()
    }
    targets = {
        name: TargetDef(name=name, **payload) for name, payload in targets_doc.items()
    }

    services: dict[str, ServiceDef] = {}
    for name, payload in services_doc.items():
        source_refs = [SourceRef(**item) for item in payload.get("sources", [])]
        target_sources: dict[str, ServiceTargetDef] = {}
        flat_sources = list(source_refs)
        target_sources_payload = payload.get("target_sources", {})
        for target_name, target_payload in target_sources_payload.items():
            target_fallback_order = list(target_payload.get("fallback_order", []))
            variants_payload = target_payload.get("variants", {})
            variants: dict[str, ServiceTargetVariantDef] = {}
            families = {}
            if variants_payload:
                for variant_name, variant_payload in variants_payload.items():
                    variant_fallback_order = list(variant_payload.get("fallback_order", []))
                    variant_families = {
                        family_name: [SourceRef(**item) for item in family_payload]
                        for family_name, family_payload in variant_payload.items()
                        if family_name not in {"primary", "fallback_order"}
                    }
                    variants[variant_name] = ServiceTargetVariantDef(
                        name=variant_name,
                        primary=bool(variant_payload.get("primary", False)),
                        families=variant_families,
                        fallback_order=variant_fallback_order,
                    )
                    for family_sources in variant_families.values():
                        flat_sources.extend(family_sources)
            else:
                families = {
                    family_name: [SourceRef(**item) for item in family_payload]
                    for family_name, family_payload in target_payload.items()
                    if family_name != "fallback_order"
                }
                for family_sources in families.values():
                    flat_sources.extend(family_sources)
            target_sources[target_name] = ServiceTargetDef(
                name=target_name,
                families=families,
                variants=variants,
                fallback_order=target_fallback_order,
            )
        services[name] = ServiceDef(
            name=name,
            enabled=bool(payload.get("enabled", True)),
            targets=list(payload.get("outputs", payload.get("targets", []))),
            sources=flat_sources,
            target_sources=target_sources,
            fallback_order=list(payload.get("fallback_order", [])),
            override=payload.get("override"),
            notes=str(payload.get("notes", "")),
        )

    bundles = {
        name: BundleDef(
            name=name,
            enabled=bool(payload.get("enabled", True)),
            targets=list(payload.get("targets", [])),
            services=list(payload.get("services", [])),
        )
        for name, payload in bundles_doc.items()
    }

    catalog = Catalog(
        root=root,
        sources=sources,
        targets=targets,
        services=services,
        bundles=bundles,
        default_fallback_order=list(
            defaults_doc.get("fallback_order", DEFAULT_FALLBACK_ORDER)
        ),
    )

    try:
        txt_snapshots = discover_txt_services(
            root, failures=catalog.self_maintained_failures
        )
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime robustness
        txt_snapshots = []
        catalog.self_maintained_failures["Source/TXT"] = str(exc)

    for snapshot in txt_snapshots:
        metadata = snapshot.metadata
        service_name = snapshot.service_name
        source_path = _relative_catalog_path(root, snapshot.source_path)
        if service_name in catalog.services:
            catalog.self_maintained_failures[source_path] = (
                f"TXT service {service_name} conflicts with existing YAML service"
            )
            continue
        known_targets = set(catalog.targets)
        service_targets = [
            target_name
            for target_name in DEFAULT_TXT_TARGETS
            if target_name in known_targets
        ]
        if not service_targets:
            catalog.self_maintained_failures[source_path] = (
                "TXT service has no supported targets in configured catalog targets"
            )
            continue
        catalog.services[service_name] = ServiceDef(
            name=service_name,
            enabled=True,
            targets=service_targets,
            notes=metadata.get("source_note", ""),
            origin=ServiceOrigin(
                kind="self_maintained",
                source_path=source_path,
                source_url=metadata.get("source_url"),
                source_note=metadata.get("source_note"),
                generated_by=metadata.get("generated_by"),
            ),
        )
        catalog.self_maintained_rules[service_name] = list(snapshot.rules)
    catalog.validate()
    return catalog
