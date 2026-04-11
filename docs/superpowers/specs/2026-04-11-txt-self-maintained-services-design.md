# TXT Self-Maintained Services Design

**Date:** 2026-04-11

**Goal:** Automatically discover `Source/TXT/*.txt` files, treat each file as a self-maintained service, and publish daily rule artifacts for `Egern`, `Loon`, `Clash`, `QuanX`, and `Shadowrocket`.

## Summary

The repository already has a target-first build pipeline driven by catalog files plus GitHub Actions. This design adds a second service source: self-maintained TXT files under `Source/TXT/`.

Each TXT file becomes one service:

- `Source/TXT/Feishu.txt` -> `Feishu`
- `Source/TXT/IyfTv.txt` -> `IyfTv`

These services are first-class outputs. They are built into the same `Rule/<Target>/<Service>/` tree as catalog-backed services, but their source of truth is the local TXT file instead of an upstream family.

## Confirmed Product Decisions

- Auto-discover `Source/TXT/*.txt`
- Default publish targets: `egern`, `loon`, `clash`, `quanx`, `shadowrocket`
- Normalize `Source/TXT/IyfTv` to `Source/TXT/IyfTv.txt`
- Service name = filename without `.txt`
- TXT format supports both explicit rule lines and relaxed shorthand
- Generated target READMEs use self-maintained wording
- If a TXT file declares a source URL, README may show the original source link

## Discovery Model

### Service Discovery

At build time, scan `Source/TXT/*.txt`. Each file yields one in-memory service definition.

Discovery rules:

- Only `.txt` files are considered
- Service name is the filename stem
- Every discovered service is enabled by default
- Every discovered service publishes to all five supported targets
- Discovered services are merged into the runtime catalog after the static YAML catalog is loaded

This avoids generating extra YAML catalog files and keeps the existing build pipeline as the single source of publishing behavior.

### Why Runtime Injection

Runtime injection was selected over generating intermediate catalog YAML because:

- it reuses the existing render pipeline
- it keeps GitHub Actions simple
- it avoids additional generated config files
- it preserves one consistent rule publication path for all service types

## TXT Source Model

### Source of Truth

TXT-backed services are canonical local sources. They do not participate in upstream family selection such as `native -> shadowrocket -> clash`.

Instead:

- parse the TXT file into normalized internal rules
- treat that parsed rule set as the service's canonical rules
- emit client-specific artifacts from that canonical set

### File Naming

Expected pattern:

- `Source/TXT/<Service>.txt`

Planned migration included in this work:

- rename `Source/TXT/IyfTv` -> `Source/TXT/IyfTv.txt`

## TXT File Format

### Supported Content

Allowed line types:

- empty lines
- comment lines starting with `#`
- metadata comment lines starting with `# @key: value`
- explicit rules such as `DOMAIN,example.com`
- relaxed shorthand domain lines such as `example.com`
- relaxed shorthand CIDR lines such as `1.2.3.0/24`

### Metadata Comments

First revision metadata keys:

- `# @source_url: <url>`
- `# @source_note: <text>`
- `# @generated_by: <text>`

Metadata is optional.

### Relaxed Rule Semantics

Shorthand conversion rules:

- bare domain -> `DOMAIN-SUFFIX,<domain>`
- bare CIDR -> `IP-CIDR,<cidr>`

Explicit rule lines continue to use the existing parser behavior when possible.

### Normalization Rules

- ignore blank lines
- ignore regular comments
- collect metadata comments separately
- preserve rule order
- deduplicate identical rules after normalization

## README Behavior

### Position

Each emitted target still publishes:

- `Rule/<TargetDir>/<Service>/<Service>.<ext>`
- `Rule/<TargetDir>/<Service>/README.md`

### Wording

TXT-backed service READMEs do not describe upstream selected families or converted upstream targets.

They instead describe:

- service name
- target client
- source file path, for example `Source/TXT/Feishu.txt`
- maintenance mode: `self-maintained`

### Optional Source Facts

If metadata is present:

- `source_url` is rendered as the original reference link
- `source_note` is rendered as a short note
- `generated_by` is rendered as generation context

Example:

- `Feishu.txt` can show the official Feishu help-center whitelist article URL
- `IyfTv.txt` can omit source URL and remain purely self-maintained

## Build Pipeline Changes

### Runtime Flow

1. Load static catalog from `catalog/*.yaml`
2. Scan `Source/TXT/*.txt`
3. Parse TXT services into runtime service definitions plus parsed rule payloads
4. Merge discovered services into the runtime catalog
5. Build target artifacts for both catalog services and TXT services
6. Render all target outputs
7. Render target READMEs with TXT-aware wording where applicable

### Failure Handling

TXT parsing failure must not break the entire publishing job.

Rules:

- if one TXT file fails to parse, report the file and the error
- continue building all other services
- do not publish new outputs for the failed TXT service
- preserve old published outputs for that service if they already exist
- do not update that service README on a failed parse

For generated TXT refresh:

- `refresh-txt-sources` should fail if a fetch/generation step fails
- if an older TXT snapshot already exists, the main build may still use that existing file

This separates source-refresh failure from artifact-generation failure and keeps daily automation stable.

## GitHub Actions Behavior

The existing daily workflow remains the primary path.

Expected order:

1. run tests
2. refresh generated TXT sources such as `Feishu.txt`
3. run `bootstrap`
4. commit changed `Source/TXT`, `Rule`, `docs`, and `dist`

This means:

- `Feishu.txt` is refreshed daily
- all TXT-backed services are re-emitted daily
- manual TXT edits such as `IyfTv.txt` flow into published target outputs automatically

## Testing Strategy

### Parser Tests

Add tests for:

- explicit TXT rule parsing
- bare domain -> `DOMAIN-SUFFIX`
- bare CIDR -> `IP-CIDR`
- comment handling
- metadata extraction
- dedupe while preserving order

### Discovery Tests

Add tests for:

- discovering `Feishu.txt` and `IyfTv.txt`
- deriving service names from filenames
- default target list = five clients
- ignoring non-`.txt` files

### Build Tests

Add tests for:

- generating all five target artifacts from a TXT-backed service
- README wording = self-maintained
- README source file path points to `Source/TXT/<Service>.txt`
- README includes `source_url` when metadata is present
- failed TXT parse does not delete old outputs

### Workflow Tests

Keep workflow coverage for:

- `refresh-txt-sources`
- `bootstrap`
- `git add Source/TXT Rule docs dist`

## File Impact

Expected implementation areas:

- `src/egloon_rule_hub/model/catalog.py`
  Runtime catalog extension for TXT-backed services
- `src/egloon_rule_hub/build.py`
  TXT-backed rule sourcing and failure-handling integration
- `src/egloon_rule_hub/docs/render.py`
  Self-maintained README rendering path
- `src/egloon_rule_hub/cli.py`
  Reuse existing bootstrap and TXT refresh entrypoints
- `src/egloon_rule_hub/txt_sources/`
  TXT discovery, metadata parsing, relaxed-line parsing
- `tests/test_txt_sources/`
  TXT parser and discovery coverage
- `tests/test_build/`
  TXT-backed build behavior
- `tests/test_cli/`
  Workflow expectations
- `Source/TXT/IyfTv.txt`
  normalized filename migration

## Non-Goals

- no per-file publish-target overrides in the first revision
- no custom README authoring per TXT file in the first revision
- no bundle auto-membership for TXT services unless later explicitly requested
- no new external storage or database

## Open Follow-Up

Future extensions can add:

- per-file target overrides
- custom README sections
- bundle inclusion metadata
- richer shorthand rules
- more generated TXT sources beyond `Feishu.txt`
