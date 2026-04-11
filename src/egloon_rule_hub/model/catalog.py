from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_FALLBACK_ORDER = ["native", "shadowrocket", "clash"]
ALLOWED_SOURCE_FAMILIES = frozenset(DEFAULT_FALLBACK_ORDER)


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
class ServiceTargetDef:
    name: str
    families: dict[str, list[SourceRef]] = field(default_factory=dict)
    fallback_order: list[str] = field(default_factory=list)

    def selected_order(self, service_fallback_order: list[str], default_order: list[str]) -> list[str]:
        if self.fallback_order:
            return self.fallback_order
        if service_fallback_order:
            return service_fallback_order
        return default_order


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


@dataclass(slots=True)
class Catalog:
    root: Path
    sources: dict[str, SourceDef]
    targets: dict[str, TargetDef]
    services: dict[str, ServiceDef]
    bundles: dict[str, BundleDef]
    default_fallback_order: list[str] = field(default_factory=lambda: DEFAULT_FALLBACK_ORDER.copy())

    def validate(self) -> None:
        known_targets = set(self.targets)
        known_sources = set(self.sources)

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
                unknown_families = sorted(
                    family for family in target_def.families if family not in ALLOWED_SOURCE_FAMILIES
                )
                if unknown_families:
                    raise ValueError(
                        f"Service {service.name} target {target_name} has unknown families: {unknown_families}"
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
            families = {
                family_name: [SourceRef(**item) for item in family_payload]
                for family_name, family_payload in target_payload.items()
                if family_name != "fallback_order"
            }
            target_sources[target_name] = ServiceTargetDef(
                name=target_name,
                families=families,
                fallback_order=target_fallback_order,
            )
            for family_sources in families.values():
                flat_sources.extend(family_sources)
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
    catalog.validate()
    return catalog
