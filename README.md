# egloon_rule_hub

Target-first proxy rule hub for Egern, Loon, Clash, QuanX, and Shadowrocket.

The project goal is simple:

- track only the rule sets we actually use
- keep a light internal model instead of hard-wiring one client format
- publish stable per-service rule URLs and bundle URLs
- publish one selected upstream family per service/target directory
- run sync and validation in GitHub Actions instead of consuming VPS resources

## Public Repo Note

This repository can be published as a public GitHub repository.

- upstream attribution is tracked in [docs/attribution.md](docs/attribution.md)
- upstream README tracking outputs are generated during `bootstrap` in [dist/manifests/upstream_docs.json](dist/manifests/upstream_docs.json) and [dist/upstream-readmes/](dist/upstream-readmes/)
- when an upstream README is unavailable, the manifest records `status: missing` with `snapshot_path: null`
- generated artifacts in `dist/` are transformed outputs built from upstream rule sources
- the repository should continue to keep upstream references visible in both the README and generated docs

## Current Stage

This repository is initialized with:

- project structure
- catalog files
- a light Python CLI
- basic parsers and emitters
- real source fetching and rule rendering for an initial `blackmatrix7` subset
- baseline GitHub Actions workflows

The current implementation fetches and renders the seeded real service artifacts with strict family selection and target-aware publication. It does not yet implement full upstream coverage or every planned adapter.

## Design Direction

- Multiple upstreams are supported, but each published service/target now selects exactly one source family.
- Family selection is strict: `native -> shadowrocket -> clash`, stop at the first non-empty family, then merge only within that family.
- Services are the main entrypoint, direct source paths and remote URLs are also supported.
- Rule-set metadata lives at the rule-set level, not on every rule line.
- Bundles reference services instead of duplicating rules.

## Published Layout

Per-service artifacts now appear under `Rule/<TargetDir>/<Service>/`, pairing the service README with the published file and selected-family provenance (for example `Rule/Clash/OpenAI/OpenAI.yaml`, `Rule/Loon/OpenAI/OpenAI.lsr`, and `Rule/Egern/OpenAI/OpenAI.yaml`). Bundles continue to publish under `dist/bundles/<bundle>/<target>.<ext>` so automation can refresh documentation and bundle outputs together.

## Supported Target Formats

- Egern rule-set YAML
- Loon `.lsr` by default
- Clash / mihomo classical rule-provider YAML
- QuanX `.list`
- Shadowrocket `.list`

## Catalog Files

- `catalog/sources.yaml`: upstream definitions
- `catalog/targets.yaml`: enabled output clients
- `catalog/services.yaml`: service catalog grouped by output target and source family
- `catalog/bundles.yaml`: grouped rule bundles

## CLI

After installing the package:

```bash
python -m egloon_rule_hub validate-catalog
python -m egloon_rule_hub render-rules
python -m egloon_rule_hub render-manifests
python -m egloon_rule_hub render-docs
python -m egloon_rule_hub bootstrap
```

`bootstrap` runs validation, target-artifact build/render, manifest rendering, upstream README snapshot rendering, and markdown doc rendering in one pass.

## Seeded Real Sources

The catalog is now wired to real upstreams:

- `blackmatrix7` as the main source for the current service set
- `ACL4SSR` as a second source for `OpenAI`, `Google`, `Telegram`, and `YouTube`

Current state:

- all cataloged services publish target-first artifacts
- Loon publishes `.lsr` by default, preserving selected-family headings/comments when available
- bundle artifacts are generated for `ai`, `china`, `commerce`, `gaming`, `google`, `social`, and `streaming`
- within-family multi-source merge remains active on the seeded overlap services listed above

This is enough to validate the real end-to-end generation path for per-service files, bundle files, selected-family provenance, and target adaptation behavior.

## GitHub Actions

- `validate.yml`: runs on push, pull request, and manual dispatch
- `sync-rules.yml`: scheduled and manual bootstrap workflow, designed to grow into the full sync pipeline

## References

- Egern rules docs: https://egernapp.com/zh-CN/docs/configuration/rules/
- Loon docs index: https://nsloon.app/docs/category/%E8%A7%84%E5%88%99/
- Loon subscription rules: https://nsloon.app/docs/Rule/sub_rule/
- mihomo rule-providers: https://wiki.metacubex.one/en/config/rule-providers/content/
- Quantumult X repo: https://github.com/kjfx/QuantumultX
- blackmatrix7 rules: https://github.com/blackmatrix7/ios_rule_script/tree/master/rule
- upstream attribution record: [docs/attribution.md](docs/attribution.md)
