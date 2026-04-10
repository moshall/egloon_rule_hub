from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


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
class ServiceDef:
    name: str
    enabled: bool
    targets: list[str]
    sources: list[SourceRef] = field(default_factory=list)
    override: str | None = None
    notes: str = ""


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


@dataclass(slots=True)
class Catalog:
    root: Path
    sources: dict[str, SourceDef]
    targets: dict[str, TargetDef]
    services: dict[str, ServiceDef]
    bundles: dict[str, BundleDef]

    def validate(self) -> None:
        known_targets = set(self.targets)
        known_sources = set(self.sources)

        for service in self.services.values():
            unknown_targets = sorted(set(service.targets) - known_targets)
            if unknown_targets:
                raise ValueError(
                    f"Service {service.name} references unknown targets: {unknown_targets}"
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
    services_doc = _load_yaml(catalog_dir / "services.yaml").get("services", {})
    bundles_doc = _load_yaml(catalog_dir / "bundles.yaml").get("bundles", {})

    sources = {
        name: SourceDef(name=name, **payload) for name, payload in sources_doc.items()
    }
    targets = {
        name: TargetDef(name=name, **payload) for name, payload in targets_doc.items()
    }

    services: dict[str, ServiceDef] = {}
    for name, payload in services_doc.items():
        source_refs = [SourceRef(**item) for item in payload.get("sources", [])]
        services[name] = ServiceDef(
            name=name,
            enabled=bool(payload.get("enabled", True)),
            targets=list(payload.get("targets", [])),
            sources=source_refs,
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
    )
    catalog.validate()
    return catalog

