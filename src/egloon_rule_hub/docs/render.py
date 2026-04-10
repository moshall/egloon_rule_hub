from __future__ import annotations

from pathlib import Path

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
        lines.append(
            f"| {name} | {service.enabled} | {', '.join(service.targets)} |"
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


def write_markdown_docs(root: Path, catalog: Catalog) -> None:
    docs_dir = root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "services.md").write_text(_services_markdown(catalog), encoding="utf-8")
    (docs_dir / "sources.md").write_text(_sources_markdown(catalog), encoding="utf-8")
    (docs_dir / "usage.md").write_text(_usage_markdown(catalog), encoding="utf-8")
    (docs_dir / "attribution.md").write_text(
        _attribution_markdown(catalog), encoding="utf-8"
    )
