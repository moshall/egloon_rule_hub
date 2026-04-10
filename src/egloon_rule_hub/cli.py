from __future__ import annotations

import argparse
import json
from pathlib import Path

from egloon_rule_hub.build import build_all_service_rules, render_rule_artifacts
from egloon_rule_hub.docs.render import write_markdown_docs
from egloon_rule_hub.model.catalog import Catalog, load_catalog


def _repo_root(path: str | None) -> Path:
    return Path(path or ".").resolve()


def _render_manifests(root: Path, catalog: Catalog) -> None:
    manifest_dir = root / "dist" / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    services = {
        name: {
            "enabled": service.enabled,
            "targets": service.targets,
            "source_count": len(service.sources),
            "notes": service.notes,
        }
        for name, service in catalog.services.items()
    }
    bundles = {
        name: {
            "enabled": bundle.enabled,
            "targets": bundle.targets,
            "services": bundle.services,
        }
        for name, bundle in catalog.bundles.items()
    }
    targets = {
        name: {"enabled": target.enabled, "file_ext": target.file_ext}
        for name, target in catalog.targets.items()
    }

    (manifest_dir / "services.json").write_text(
        json.dumps(services, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (manifest_dir / "bundles.json").write_text(
        json.dumps(bundles, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (manifest_dir / "targets.json").write_text(
        json.dumps(targets, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_validate(root: Path) -> Catalog:
    catalog = load_catalog(root)
    print(
        "Catalog OK:"
        f" sources={len(catalog.sources)}"
        f" targets={len(catalog.targets)}"
        f" services={len(catalog.services)}"
        f" bundles={len(catalog.bundles)}"
    )
    return catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="egloon-rule-hub")
    parser.add_argument("--root", default=".", help="Repository root path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-catalog", help="Validate catalog files")
    subparsers.add_parser("render-rules", help="Fetch sources and render rule artifacts")
    subparsers.add_parser("render-manifests", help="Render JSON manifests")
    subparsers.add_parser("render-docs", help="Render markdown docs")
    subparsers.add_parser(
        "bootstrap",
        help="Validate catalog and render generated docs and manifests",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = _repo_root(args.root)

    if args.command == "validate-catalog":
        _run_validate(root)
        return 0

    if args.command == "render-manifests":
        catalog = _run_validate(root)
        _render_manifests(root, catalog)
        print(f"Rendered manifests to {root / 'dist' / 'manifests'}")
        return 0

    if args.command == "render-rules":
        catalog = _run_validate(root)
        service_rules = build_all_service_rules(catalog)
        render_rule_artifacts(root, catalog, service_rules)
        print(f"Rendered rule artifacts to {root / 'dist'}")
        return 0

    if args.command == "render-docs":
        catalog = _run_validate(root)
        write_markdown_docs(root, catalog)
        print(f"Rendered docs to {root / 'docs'}")
        return 0

    if args.command == "bootstrap":
        catalog = _run_validate(root)
        service_rules = build_all_service_rules(catalog)
        render_rule_artifacts(root, catalog, service_rules)
        _render_manifests(root, catalog)
        write_markdown_docs(root, catalog)
        print("Bootstrap complete")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
