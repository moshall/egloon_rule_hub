# Publish-Repo Icons, QuantumultX, and Bundles Design

## Goal

Change `egloon_rule_hub` from a mixed development-and-publish repository into a publish-first repository on `main`, while expanding the public rule surface in a strict and predictable way.

This slice combines five related changes that should ship together:

- convert the public repository into a lean publish repository
- replace public `QuanX` naming with `QuantumultX`
- add a new batch of upstream-backed services
- attach strict upstream-matched icons into each published service directory
- expand bundle generation with new grouped rule outputs

The result should be a repository whose public branch is easy to consume:

- stable per-service directories
- stable bundle outputs
- optional per-service `icon.png`
- strict provenance
- no public development-only folders such as `docs/` or `tests/`

## Scope

This slice should cover:

- renaming the published `QuanX` target to `QuantumultX`
- updating upstream source resolution so the QuantumultX target reads from `rule/QuantumultX/...`
- expanding the service catalog with the newly requested upstream-backed services that have real source coverage
- keeping unsupported services out of publication under strict mode
- adding icon synchronization from `Keviin560/icon`
- publishing matched icons into each `Rule/<Target>/<Service>/` directory
- surfacing icon availability in generated README files and manifests
- extending bundle definitions with `AI` and `ChinaBank`
- removing public `docs/`, `tests/`, and other non-essential tracked folders from the publish branch
- narrowing GitHub Actions auto-commit scope to publish artifacts and minimal generation code only

This slice should not cover:

- fuzzy icon matching
- service-name alias fallback for missing icons
- synthetic rule creation for services that do not exist in upstream
- introducing a separate development branch or separate repository
- preserving backward compatibility for `Rule/QuanX/`

## User Decisions Locked In

The user explicitly chose the following:

- public branch model: `main` is the publish repository
- icon/rule source matching mode: strict
- QuantumultX naming mode: fully public `QuantumultX`, no public `QuanX`
- GitHub visibility rule: do not keep `docs/`, `tests/`, or similar development-only folders in the public repository

These decisions are binding for this slice.

## Problem Statement

The repository currently still behaves like an internal build workspace even though the user wants it to serve as a clean public publish repository.

That creates five concrete problems.

### 1. The public branch contains development-only material

Today the repository still tracks:

- `docs/`
- `tests/`
- design and planning files under `docs/superpowers/`

Those files are useful during development, but they are not part of the public rule product.

For a consumer browsing the repository, this adds noise and makes the branch look like an implementation workspace instead of a distribution surface.

### 2. QuantumultX is represented inconsistently

Internally and publicly the repository still uses `QuanX` in several places:

- directory names such as `Rule/QuanX/...`
- display labels
- documentation text

But the real upstream target family in `blackmatrix7` is `QuantumultX`.

This mismatch makes the source selection model less clear and pushes public naming away from the real upstream structure.

### 3. Icons are missing from published service directories

The user wants each rule directory to look more like a complete content pack.

Right now a published service directory contains:

- the rule file
- a README

It does not contain a matching icon, even when an upstream icon exists.

### 4. The service catalog is still smaller than the desired public rule surface

The current catalog covers the initial seed set, but the user requested a larger set of public services, especially:

- infrastructure and direct-routing services
- China ecosystem services
- bank-related services
- more Apple ecosystem services

Without these additions, the repository still falls short of the requested operating surface.

### 5. Bundle grouping is still too narrow

The current bundle model already exists, but it does not yet expose the user-requested grouped outputs:

- `AI`
- `ChinaBank`

The missing grouped bundles mean downstream clients still need to subscribe to more service-level feeds manually than the user wants.

## Strict-Mode Product Rules

This slice uses strict mode everywhere unless the user changes the policy later.

Strict mode means:

- no guessed rule source
- no guessed icon
- no service publication when the rule source does not exist upstream
- no service publication when the requested icon does not have a strict upstream file match

Strict mode does not mean the service is rejected entirely when icon data is missing.

Instead:

- rules may still publish if upstream rules exist
- `icon.png` is only published when a strict match exists
- README should state when icon data is unavailable

## Public Repository Shape After This Change

The target public repository should keep only the minimum public surface necessary to regenerate and publish rule outputs.

### Kept in `main`

- `.github/workflows/`
- `catalog/`
- `src/egloon_rule_hub/`
- `Source/TXT/`
- `Rule/`
- `dist/`
- `README.md`
- a root-level attribution document if needed for public upstream visibility

### Removed from `main`

- `docs/`
- `tests/`
- `docs/superpowers/`
- other development-only directories that are not required for public regeneration or publication

This is intentionally a publish-first repository, not a developer-first repository.

## QuantumultX Naming Decision

### Public target identity

The public target must become `QuantumultX`.

Examples of the new published layout:

- `Rule/QuantumultX/OpenAI/OpenAI.list`
- `Rule/QuantumultX/Discord/Discord.list`
- `Rule/QuantumultX/AppleMusic/AppleMusic.list`

### Internal model

The internal target key should also move from `quanx` to `quantumultx`.

This keeps the model aligned across:

- catalog
- build logic
- docs generation
- manifest generation
- output directories

This is preferable to keeping an internal alias because the user explicitly chose full public renaming rather than compatibility mode.

### Upstream source path mapping

For the `quantumultx` target, the default native source family should resolve to:

- `rule/QuantumultX/<Service>/<Service>.list`

The repository should no longer use `QuanX` as a source-family directory guess.

### Cleanup behavior

When rendering artifacts:

- stale `Rule/QuanX/` directories must be pruned
- stale bundle files using the old target name must be pruned if they exist

## Icon Synchronization Design

### Upstream source

The icon source is:

- repository: `Keviin560/icon`
- path root: `src/`

The icon input space is a flat upstream file collection.

### Matching rule

Only strict exact-name matches are allowed.

Allowed match form:

- `<Service>.png`

Examples:

- service `Claude` may match `Claude.png`
- service `Discord` may match `Discord.png`
- service `Notion` may match `Notion.png`

Not allowed:

- inferred semantic matches such as `OpenAI -> ChatGPT`
- inferred brand matches such as `AppStore -> App Store`
- partial heuristics such as `Twitter -> X`

### Published location

When an icon is matched, it should be copied into every published service target directory:

- `Rule/Clash/Discord/icon.png`
- `Rule/Egern/Discord/icon.png`
- `Rule/Loon/Discord/icon.png`
- `Rule/QuantumultX/Discord/icon.png`
- `Rule/Shadowrocket/Discord/icon.png`

This is intentionally repeated instead of centralized so each service directory is self-contained.

### README behavior

Each service README should include one icon line:

- matched case: `- Icon: [icon.png](./icon.png)`
- missing case: `- Icon: unavailable (strict upstream match not found)`

### Manifest behavior

The build should generate an icon manifest under `dist/manifests/icons.json`.

Each service record should state:

- whether an icon was matched
- which upstream icon file was used when matched
- why the icon is unavailable when unmatched

Example unavailable reasons:

- `strict_match_not_found`
- `icon_sync_source_unavailable`

### Synchronization timing

Icon synchronization should happen inside the normal public refresh flow before README generation, so generated READMEs can reference the final icon presence correctly.

## New Service Expansion

The user requested these additional services:

- `Direct`
- `Discord`
- `Disney`
- `Naver`
- `JianGuoYun`
- `MEGA`
- `Notion`
- `OKX`
- `TIDAL`
- `TestFlight`
- `iCloud`
- `GoogleFCM`
- `ChinaMedia`
- `CMB`
- `CEB`
- `CCB`
- `CGB`
- `CIBN`
- `CNN`
- `CNNIC`
- `ChinaIPs`
- `ChinaDNS`
- `ChinaASN`
- `BesTV`
- `BardAI`
- `BOC`
- `BOCOM`
- `AppleTV`
- `AppleProxy`
- `AppleMusic`
- `AppleID`
- `AppStore`
- `Apkpure`
- `Android`
- `AirChina`
- `PSBC`
- `Tesla`

### Upstream availability result

Based on current upstream inspection against `blackmatrix7`, this slice should publish all of the above except:

- `ChinaASN`

Reason:

- `ChinaASN` does not currently have a matching upstream rule directory in the inspected `blackmatrix7` source set

`ChinaIPs` and `ChinaDNS` already exist in the repository and should remain part of the catalog rather than being duplicated.

### Strict exclusion set

The requested bundle note also mentioned:

- `X`
- `Grok`

Those names currently do not have strict upstream rule directories in the inspected rule source set.

Therefore this slice should not add them as publishable services.

Under strict mode they may only be added later when real upstream rule directories exist.

## Bundle Expansion

The repository already supports grouped bundle outputs under `dist/bundles/<bundle>/`.

This slice should add or update the following groups.

### `ai`

The `ai` bundle should include:

- `OpenAI`
- `Claude`
- `Gemini`
- `BardAI`

It should also include:

- `Twitter`

because the user explicitly wants that service inside the AI-oriented group for downstream use.

It should not include:

- `X`
- `Grok`

because those services do not exist as strict publishable services in this slice.

### `china-bank`

Create a new bundle:

- bundle key: `china-bank`
- public label in docs: `ChinaBank`

Services:

- `CCB`
- `CEB`
- `CGB`
- `CMB`
- `PSBC`

The bundle path should remain filesystem-stable and lowercase:

- `dist/bundles/china-bank/`

## README and Public Documentation Behavior

The repository will no longer publish `docs/` in the final public form, so public-facing explanation should move to:

- root `README.md`
- per-service `Rule/<Target>/<Service>/README.md`
- generated manifests under `dist/manifests/`

That means:

- the root README must explain the publish-first repository model
- the root README must use `QuantumultX` instead of `QuanX`
- per-service README files must surface icon availability
- manifest files become the structured machine-readable public metadata layer

## Workflow Behavior

### Validate workflow

The public repository may still run lightweight validation in GitHub Actions, but it must not depend on tracked `tests/` if those files are removed from the public branch.

This means validation should be narrowed to checks that still make sense in the publish repository, for example:

- catalog load succeeds
- bootstrap succeeds

### Sync workflow

The sync workflow should:

1. refresh generated TXT sources
2. refresh icon source snapshot if the implementation keeps a local source cache
3. run bootstrap
4. stage only public repository content
5. commit only when public outputs changed

The stage scope should exclude:

- `docs/`
- `tests/`
- temporary planning/spec folders

## Data Model Changes

This slice needs one new public metadata concept:

- icon match metadata per service

It may be represented either:

- as a dedicated manifest structure, or
- as extra fields attached to service publication records

A dedicated manifest is preferred because it keeps icon concerns out of the rule-source provenance model.

Suggested manifest shape:

```json
{
  "Discord": {
    "matched": true,
    "source_repo": "Keviin560/icon",
    "source_path": "src/Discord.png",
    "published_filename": "icon.png"
  },
  "OpenAI": {
    "matched": false,
    "reason": "strict_match_not_found"
  }
}
```

## Output Examples

### Service directory with icon

```text
Rule/Clash/Discord/
  Discord.yaml
  README.md
  icon.png
```

### Service directory without icon

```text
Rule/Clash/OpenAI/
  OpenAI.yaml
  README.md
```

README example line:

```text
- Icon: unavailable (strict upstream match not found)
```

### QuantumultX directory

```text
Rule/QuantumultX/Discord/
  Discord.list
  README.md
  icon.png
```

## Migration Notes

This slice is allowed to be breaking in public path shape.

Breaking changes:

- `Rule/QuanX/...` becomes `Rule/QuantumultX/...`
- public repository no longer contains `docs/`
- public repository no longer contains `tests/`

These are acceptable because the user explicitly chose the clean publish-first model over compatibility.

## Acceptance Criteria

After `python -m egloon_rule_hub bootstrap`:

- `Rule/QuantumultX/` exists
- `Rule/QuanX/` does not remain
- newly added strict-source services publish for all enabled targets they support
- unsupported requested services such as `ChinaASN` are absent rather than guessed
- matched icons appear as `icon.png` inside each published service target directory
- unmatched icons do not create guessed files
- per-service README files state icon availability
- `dist/manifests/icons.json` exists
- the `ai` bundle includes `BardAI`
- the `china-bank` bundle exists and contains the requested bank services
- public repository staging excludes `docs/` and `tests/`

## Risks

### 1. Public branch becomes harder to develop in directly

This is a deliberate tradeoff of the publish-first model.

The branch becomes easier to consume and slightly harder to extend casually.

### 2. Strict icon matching will leave some services without icons

This is expected behavior, not a defect.

Examples likely to remain without strict icon matches based on current inspection:

- `OpenAI`
- `Twitter`
- several bank and Apple-subservice names

### 3. Removing tests from the public branch reduces visible safety rails

This is an accepted consequence of using `main` as the publish branch.

The implementation should still preserve enough runtime validation so the public workflow does not become blind.

## Temporary Planning Note

This specification is being written under `docs/superpowers/specs/` only as a temporary planning artifact during implementation.

The final public repository shape defined by this spec still requires removing `docs/` from the published branch once the feature work is complete.
