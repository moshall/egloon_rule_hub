# egloon_rule_hub Design

## Goal

Build a GitHub Actions driven rule hub that tracks selected upstream proxy rule sets, normalizes them into a light internal model, and emits stable artifacts for Egern, Loon, Clash, QuanX, and Shadowrocket.

## Scope

The first milestone is repository initialization, not full rule synchronization. It should establish:

- repository structure
- catalog contracts
- lightweight CLI
- basic parser and emitter boundaries
- baseline docs
- GitHub Actions validation and bootstrap workflows

## Core Decisions

### 1. Multi-source by design

The system must support multiple upstreams even if the first wired source is `blackmatrix7`. A service may merge multiple sources by priority, and future sources can be added without redesigning the repository.

### 2. Service-first with direct source escape hatch

Normal maintenance should happen at the service level, for example `OpenAI` or `GitHub`. The data model also allows direct source paths or raw URLs for special cases so the project does not get blocked by catalog abstraction limits.

### 3. Rule-set metadata only

Metadata belongs to the rule set. Individual rules should stay light, mostly `type + value`. Local edits happen through override files instead of attaching heavy provenance to every line.

### 4. Stable per-service and bundle outputs

The repository should eventually publish both:

- per-service artifacts
- grouped bundle artifacts, such as `ai`, `streaming`, or `social`

### 5. Standard model before output format

The implementation should normalize rules into an internal model first, then emit client-specific files. This avoids string-replacement spaghetti once additional upstreams and clients are added.

## Repository Layout

The repository is organized into catalog, source adapters, parsers, normalization, emitters, generated output, and docs. This keeps input definition, transformation logic, and published artifacts separate.

## First Implementation Slice

The first initialization should ship:

- `catalog/*.yaml`
- `overrides/services/OpenAI.yaml`
- Python package skeleton under `src/egloon_rule_hub`
- basic catalog validation
- rule parser and emitter placeholders with basic functionality
- docs rendering from catalog
- manifest rendering into `dist/manifests`
- GitHub Actions workflows

## Non-Goals for Initialization

- complete upstream fetch pipeline
- full merge policy implementation for every edge case
- full client compatibility parity
- automated publishing to a live GitHub repo

Those come after the repository skeleton is stable.

