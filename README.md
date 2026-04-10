# egloon_rule_hub

Multi-source proxy rule hub for Egern, Loon, Clash, QuanX, and Shadowrocket.

The project goal is simple:

- track only the rule sets we actually use
- keep a light internal model instead of hard-wiring one client format
- publish stable per-service rule URLs and bundle URLs
- run sync and validation in GitHub Actions instead of consuming VPS resources

## Public Repo Note

This repository can be published as a public GitHub repository.

- upstream attribution is tracked in [docs/attribution.md](/home/dev/dev/repos/egloon_rule_hub/docs/attribution.md)
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

The current implementation already fetches and renders a first batch of real service artifacts. It does not yet implement full upstream coverage, advanced merge policy controls, or a complete adapter set for every planned source.

## Design Direction

- Multiple upstreams are supported at the data model level.
- Services are the main entrypoint, direct source paths and remote URLs are also supported.
- Rule-set metadata lives at the rule-set level, not on every rule line.
- Bundles reference services instead of duplicating rules.

## Supported Target Formats

- Egern rule-set YAML
- Loon `.list`
- Clash / mihomo classical rule-provider YAML
- QuanX `.list`
- Shadowrocket `.list`

## Catalog Files

- `catalog/sources.yaml`: upstream definitions
- `catalog/targets.yaml`: enabled output clients
- `catalog/services.yaml`: service-level rule catalog
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

`bootstrap` runs validation, source fetch, rule rendering, manifest rendering, and markdown doc rendering in one pass.

## Seeded Real Sources

The catalog is now wired to real upstreams:

- `blackmatrix7` as the main source for the current service set
- `ACL4SSR` as a second source for `OpenAI`, `Google`, `Telegram`, and `YouTube`

Current state:

- all 61 requested services are cataloged
- 61 per-service artifacts are generated for each target format
- bundle artifacts are generated for `ai`, `china`, `commerce`, `gaming`, `google`, `social`, and `streaming`
- multi-source merge is active on the seeded overlap services listed above

This is enough to validate the first real end-to-end generation path for per-service files, bundle files, and upstream-priority merge behavior.

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
- upstream attribution record: [docs/attribution.md](/home/dev/dev/repos/egloon_rule_hub/docs/attribution.md)
