# Target-Native Fallback Design

## Goal

Change `egloon_rule_hub` from a service-first multi-source merge model into a target-first source selection model.

After this change, each service/target artifact should answer one simple question clearly:

`Which upstream target did this file come from?`

The answer should be deterministic:

- prefer the target's native upstream source
- if no native source exists, fall back to `shadowrocket`
- if no `shadowrocket` source exists, fall back to `clash`
- once a source family is selected, stop and use only that family

This should remove the current ambiguity where generated targets such as `Egern` appear to be built from a blended service-level source pool even when the desired behavior is closer to "pick the best upstream target source, then adapt if needed."

## Scope

This slice changes how service sources are modeled, selected, documented, and tested.

It should cover:

- redesigning the service catalog so source definitions are grouped by target
- introducing default target fallback order of `native -> shadowrocket -> clash`
- allowing per-target or per-service fallback override only when explicitly configured
- changing build selection from "merge every listed source for the service" to "select one source family for the service/target output"
- preserving direct copy behavior for native outputs when source format already matches the target format
- preserving adapter-based conversion when the selected source family does not match the output target
- updating README provenance so it states the selected source family and conversion path
- updating manifests and tests to reflect the selected source family instead of service-wide merged provenance

It should not cover:

- redesigning bundle output layout
- adding new target types in this same slice
- rewriting every upstream source registry implementation
- preserving compatibility with the old `services.yaml` schema

## Problem Statement

The current model stores service sources in one flat list and then merges them before rendering all targets.

That causes three problems:

### 1. Provenance is harder to understand than the actual behavior users expect

A user looking at:

- `Rule/Egern/Apple/Apple.yaml`

expects to learn which upstream target was used for that Egern file.

The current service-level merge model instead says, effectively:

- these Loon and Clash sources were all merged for the service
- then the merged rule set was emitted into Egern

That is technically consistent with the current pipeline, but not with the mental model users naturally apply when browsing target-specific directories.

### 2. We do unnecessary second-stage adaptation

If the target being published already has a native source in upstream, the best answer is usually to use it directly.

The current pipeline still normalizes all listed sources into one shared service rule set before emitting every target, which means native targets and converted targets are treated too similarly.

### 3. README wording becomes misleading

For converted targets, the README should explain which upstream target family was selected and adapted.

For native targets, the README should explain that the published artifact mirrors the native upstream target.

The current manifest structure does not represent that distinction cleanly enough.

## User-Facing Outcome

After `python -m egloon_rule_hub bootstrap`, each published service/target directory should describe one selected source family.

Examples:

- `Rule/Clash/Apple/Apple.yaml` should normally select the native Clash source family
- `Rule/Loon/Apple/Apple.list` should normally select the native Loon source family
- `Rule/Egern/Apple/Apple.yaml` should normally select the best available fallback family for Egern, based on configured order

If `Egern` has no native upstream source but has Shadowrocket and Clash source families configured, the generated artifact should:

- select `shadowrocket`
- convert from Shadowrocket rules into Egern format
- say that selection plainly in `Rule/Egern/Apple/README.md`

If `Egern` later gains native upstream sources, the same artifact should:

- select `native`
- stop there
- publish the native Egern output directly
- say the directory mirrors the native Egern upstream

## Core Decisions

### 1. Services become target-scoped source maps

The service catalog should no longer define one flat `sources` list.

Instead, each service should define sources under each output target.

Conceptually:

```yaml
defaults:
  fallback_order: [native, shadowrocket, clash]

services:
  Apple:
    enabled: true
    targets:
      egern:
        native: []
        shadowrocket: []
        clash: []
      clash:
        native: []
      loon:
        native: []
```

This makes the source choice explicit at the place where the output target is defined.

### 2. Default fallback order is global and strict

The default selection order for every target should be:

1. `native`
2. `shadowrocket`
3. `clash`

Selection is strict:

- inspect the candidates in order
- choose the first non-empty source family
- ignore lower-priority families

This is not a merge strategy.
It is a family selection strategy.

### 3. Native means "native for the output target"

`native` is a relative slot, not a literal upstream client name.

Examples:

- for output target `clash`, `native` means Clash-native upstream sources
- for output target `loon`, `native` means Loon-native upstream sources
- for output target `egern`, `native` means Egern-native upstream sources

This keeps fallback order compact while still being target-relative.

### 4. Per-service overrides remain possible, but opt-in

Most services should use the global default fallback order.

If a specific service/target needs a different order, it may define an explicit override.

This should be rare and should not be required for normal operation.

Examples of acceptable override use:

- a target where Shadowrocket sources are known to be lower quality than Clash for a specific service
- a service whose native upstream artifacts are incomplete and should temporarily fall back to another family

### 5. Selected family sources may still contain multiple entries

The selected family may still contain more than one source entry.

For example, a service may choose:

- selected family: `clash`
- entries: `blackmatrix7 Clash`, `ACL4SSR Clash`

Those entries may still be merged and deduplicated within that selected family.

What changes is the boundary:

- merge within the selected family only
- do not merge across fallback families

### 6. Native-match outputs should be direct where possible

If the selected family format already matches the output target format, publishing should remain as direct as practical.

That means:

- parse for normalization and validation as needed
- but keep the provenance classified as native/direct
- do not describe the output as converted

This matters for README semantics more than for internal implementation detail.

### 7. Converted outputs must describe the actual source family

If an output target uses a non-native selected family, the README must say:

- which family was selected
- which source entries were used
- which upstream target family those entries belong to
- which conversion path was applied

Example:

`This Egern artifact is generated from the selected Shadowrocket source family for Apple.`

## Catalog Model

### Current shape

Today, a service roughly looks like this:

```yaml
services:
  Apple:
    enabled: true
    targets: [egern, loon, clash, quanx, shadowrocket]
    sources:
      - source: blackmatrix7
        path: rule/Clash/Apple/Apple.yaml
        format: clash_yaml
      - source: blackmatrix7
        path: rule/Loon/Apple/Apple.list
        format: loon_list
```

This shape is optimized for a service-wide merge model.

### Target-first shape

After the redesign, a service should roughly look like this:

```yaml
defaults:
  fallback_order: [native, shadowrocket, clash]

services:
  Apple:
    enabled: true
    outputs: [egern, loon, clash, quanx, shadowrocket]
    target_sources:
      egern:
        native: []
        shadowrocket:
          - source: blackmatrix7
            path: rule/Shadowrocket/Apple/Apple.list
            format: shadowrocket_list
            priority: 100
        clash:
          - source: blackmatrix7
            path: rule/Clash/Apple/Apple.yaml
            format: clash_yaml
            priority: 90
      clash:
        native:
          - source: blackmatrix7
            path: rule/Clash/Apple/Apple.yaml
            format: clash_yaml
            priority: 100
      loon:
        native:
          - source: blackmatrix7
            path: rule/Loon/Apple/Apple.list
            format: loon_list
            priority: 100
```

The exact key names may vary in implementation, but the behavior must encode:

- output target name
- available source families for that output target
- zero or more source refs per family
- optional override of fallback order when explicitly needed

### Validation requirements

Catalog validation should ensure:

- every declared output target exists in `catalog/targets.yaml`
- every source ref still resolves to a known source definition
- every source ref still has `path` or `url`
- fallback family keys are from an allowed set
- any custom fallback order only references allowed families
- any output target with no resolvable family is allowed to remain unpublished, but this should be explicit in diagnostics

## Source Family Semantics

The allowed default family keys in this slice should be:

- `native`
- `shadowrocket`
- `clash`

They mean:

- `native`: upstream rules already written for the output target
- `shadowrocket`: upstream rules written in Shadowrocket-compatible syntax
- `clash`: upstream rules written in Clash-compatible syntax

This slice does not require adding `loon` or `quanx` as fallback families by default.

Those families may still exist as native sources for their own output targets.

## Selection Algorithm

For each `service_name` and `target_name`:

1. load the configured source families for that service/target
2. load the fallback order
   - per-target override if present
   - otherwise per-service override if present
   - otherwise global default `native -> shadowrocket -> clash`
3. walk the order from first to last
4. choose the first family with at least one source ref
5. merge and dedupe only the entries inside that chosen family
6. render the output for the target using the existing target emitter
7. record provenance based on the chosen family

If no family has sources:

- skip publishing that target/service artifact
- expose that state in docs/manifests/tests in a deterministic way

## Build Pipeline Changes

### Current behavior

Today the build pipeline:

1. iterates one flat source list for the service
2. parses all of them into one merged service rule set
3. emits every output target from that shared service rule set

### New behavior

After this slice, the build pipeline should:

1. iterate the service's output targets
2. select one source family for that service/target pair
3. resolve and parse only the source refs in that family
4. merge and dedupe only those rules
5. emit the target artifact

This means there is no single universal service rule set anymore.

Instead, there is a target-specific selected rule set.

That is the intended behavior.

## Adapter Rules

The existing parser/emitter architecture is still useful and should stay.

Examples:

- if selected family is `native` for `clash`, parse as Clash and emit Clash
- if selected family is `shadowrocket` for `egern`, parse as Shadowrocket and emit Egern
- if selected family is `clash` for `egern`, parse as Clash and emit Egern

The important semantic distinction is:

- same-family target output is classified as direct/native
- different-family target output is classified as converted

This classification should be explicit in manifests and READMEs.

## README Contract

Each `Rule/<Target>/<Service>/README.md` should clearly state the selected family.

### Native case

If `native` is selected:

- say the directory mirrors the native upstream target
- show the native upstream rule and README URLs
- do not describe the artifact as converted

### Converted case

If `shadowrocket` or `clash` is selected for a different output target:

- say the directory is generated by `egloon_rule_hub`
- say which family was selected
- say which conversion path was used, for example `Shadowrocket -> Egern`
- show only the selected family's upstream sources

### Selected-family-only provenance

The README should no longer show upstream entries from families that lost the selection decision.

Example:

If `Rule/Egern/Apple/README.md` selects `shadowrocket`, it should not also list Clash entries just because they are available as a lower fallback.

That would reintroduce the same ambiguity this redesign is meant to remove.

## Manifest Contract

The upstream docs manifest and any related internal manifests should be updated to include selected-family facts such as:

- `target`
- `target_dir`
- `service`
- `selected_family`
- `selected_native_target`
- `is_native`
- `is_converted`
- `conversion_path`

If the selected family contains multiple source entries, each manifest row may still represent one entry, but each row must repeat the same selection metadata for that service/target build.

The manifest should not imply that lower fallback families participated when they did not.

## Data Migration Strategy

This slice may break the current `catalog/services.yaml` schema.

That is acceptable.

The repository is still early enough that clarity is more important than preserving the old shape.

Migration expectations:

- replace the old flat service `sources` list with target-scoped source families
- update catalog loaders and validators accordingly
- update any tests or docs that still assume a service-wide merged source list

## Testing Requirements

The redesign should add or update tests for:

### Catalog loading

- loading target-scoped source family config
- rejecting unknown family keys
- rejecting unknown targets in output declarations
- honoring explicit fallback override when configured

### Selection

- selecting `native` when present
- selecting `shadowrocket` when native is absent
- selecting `clash` when native and shadowrocket are absent
- skipping publish when all families are empty
- ensuring lower fallback families are not included after a higher family wins

### Rendering

- native target README wording
- converted target README wording
- selected-family-only provenance in README
- correct conversion path labeling

### End-to-end bootstrap

- representative native case
- representative fallback-to-shadowrocket case
- representative fallback-to-clash case
- stable publish layout under `Rule/<Target>/<Service>/`

## Open Implementation Decisions

The implementation may choose either of these internal shapes:

### Option A: new `TargetServiceDef` model

Introduce a dedicated nested dataclass structure for service target config.

This is cleaner and should be preferred if the code stays readable.

### Option B: normalize nested YAML into existing `SourceRef` plus metadata

Reuse more of the current model layer and add selection metadata around it.

This may reduce churn, but should not compromise clarity.

The implementation plan should choose one and keep the model easy to reason about.

## Non-Goals

This slice should not:

- reintroduce service-wide multi-family merges as the default behavior
- pretend converted outputs are native
- list unused fallback families in target READMEs
- optimize for backward schema compatibility at the expense of clarity

## Acceptance Criteria

This design is complete when all of the following are true:

1. A service/target output selects exactly one source family by strict order.
2. The default strict order is `native -> shadowrocket -> clash`.
3. A selected `native` family stops fallback traversal and excludes lower families.
4. A selected `shadowrocket` family stops fallback traversal and excludes `clash`.
5. Multiple source refs may still merge within the selected family only.
6. `Rule/<Target>/<Service>/README.md` names the selected family and conversion path correctly.
7. A converted target README never lists lower-priority families that were not selected.
8. A native target README is classified as native/direct, not converted.
9. Bootstrap and tests cover native selection, fallback selection, and skipped targets.
