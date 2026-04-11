# Upstream README Tracking Design

## Goal

Extend `egloon_rule_hub` so each service can track the upstream README content that explains how the source rule set should be used, while keeping the workflow GitHub Actions driven and fact-based.

The new behavior should let a reader open a service page and see:

- the service summary
- the exact upstream rule file links currently used by this repository
- the exact upstream README links currently associated with those rule files
- a short local summary for quick reading
- the upstream README original text, shown as-is

## Scope

This slice adds upstream README tracking for service documentation. It does not redesign the rule model, source catalog shape, or publish flow.

It should cover:

- README discovery from existing `service.sources[*]`
- README fetch and snapshot storage
- machine-readable manifest output for README tracking
- per-service markdown detail pages
- service index links to detail pages
- strict missing handling with no invented content

It should not cover:

- semantic merging of different upstream README texts into a rewritten synthetic document
- manual README metadata fields inside `catalog/services.yaml`
- fallback inference from unrelated directories or repository-wide docs
- any new deployment surface outside the existing GitHub Actions workflows

## User-Facing Outcome

After `python -m egloon_rule_hub bootstrap`, the repository should publish:

- the existing generated rule artifacts in `dist/`
- README snapshots in `dist/upstream-readmes/`
- README tracking metadata in `dist/manifests/upstream_docs.json`
- a linked service index in `docs/services.md`
- a service detail page for each service under `docs/services/`

The service detail page is the main entrypoint. It should be possible to inspect a service such as `OpenAI` and immediately see which upstream rule files are used, where the README lives, and what the upstream README actually says.

## Core Decisions

### 1. Service page is the primary view

The repository should stay service-first. Users should not have to browse by upstream repository or folder to understand a service.

The service index page should stay compact and link to the detail pages instead of trying to render full README content inline.

### 2. Original upstream text must stay original

The upstream README content should be shown as original text, not rewritten into a fake unified upstream narrative.

The detail page may contain a local summary block above the upstream text, but the original text should still appear in source-separated sections.

### 3. Strict mode for missing upstream docs

If a source directory does not provide a `README.md`, the system should state that plainly as `upstream README missing`.

The system must not infer README content from naming conventions, neighboring folders, or repository-level docs.

### 4. Multi-source services stay multi-source

For services that consume more than one upstream, the detail page should include each referenced upstream source.

The page may provide one local summary for the overall service, but the original upstream content must remain separated by source so readers can verify what came from where.

### 5. Snapshot first, markdown second

README fetch should happen before markdown rendering and should produce stable intermediate artifacts.

Markdown rendering should consume the snapshot output instead of performing network requests directly. This keeps the render step deterministic and easier to test.

## Data Flow

The new flow should be:

1. Load catalog as usual.
2. Resolve each `service.sources[*]` into the exact upstream rule file URL already used for rule generation.
3. Derive a sibling `README.md` URL from the resolved rule file location.
4. Fetch the README content if present.
5. Write a snapshot file and a structured manifest record for each service/source pair.
6. Render service index and detail pages from the manifest and snapshots.

This keeps the source of truth simple:

- `catalog/` defines what we use
- source resolvers define where those files live upstream
- README tracking derives documentation URLs from those same resolved source locations

## Output Structure

### Snapshot files

Write raw upstream README content to:

`dist/upstream-readmes/<Service>/<source>/README.md`

Only write the file when fetch succeeds. Missing or fetch-error states should be represented in the manifest and markdown output, not by inventing placeholder README files.

### Manifest

Write a machine-readable manifest to:

`dist/manifests/upstream_docs.json`

Each service entry should include enough information for docs rendering and later tooling. At minimum:

- service name
- source name
- source priority
- upstream rule file URL
- upstream README URL
- fetch status: `ok`, `missing`, or `fetch_error`
- local snapshot path when status is `ok`

### Service index

`docs/services.md` should remain the high-level table but the service name should link to:

`docs/services/<Service>.md`

The index should stay concise. It does not need to inline the README content.

### Service detail page

Each detail page should be generated at:

`docs/services/<Service>.md`

Recommended section order:

1. service title
2. local summary
3. upstream rule file links
4. upstream README links
5. upstream original text sections, grouped by source
6. factual notes, such as missing README count or fetch-error count

For multi-source services, the page should show all sources in one service page, but the upstream original text should still be separated by source block.

## File Boundaries

### `src/egloon_rule_hub/upstream_docs/fetch.py`

Purpose:

- derive README URLs from resolved rule file URLs
- fetch README text
- normalize fetch result state

This module should not render markdown or write service docs.

### `src/egloon_rule_hub/upstream_docs/build.py`

Purpose:

- iterate through catalog services and sources
- collect README tracking records
- write snapshot files under `dist/upstream-readmes/`
- write `dist/manifests/upstream_docs.json`

This module is the boundary between network fetch and static output.

### `src/egloon_rule_hub/docs/render.py`

Extend the existing docs renderer to:

- load upstream docs manifest data
- write service detail pages
- update the service index to link to detail pages

This module should not perform network fetches.

### `src/egloon_rule_hub/cli.py`

Extend `bootstrap` so it:

- validates catalog
- renders rules
- renders manifests
- builds upstream README snapshots and manifest
- renders docs

The CLI should stay small. There is no need to add a separate user-facing command unless future maintenance proves it necessary.

## Error Handling

### Rule fetch failure

If the upstream rule file itself cannot be fetched, bootstrap should still fail. That is a core pipeline failure.

### README missing

If the derived `README.md` returns a real not-found result, record `missing` and continue.

Markdown output should show the README URL and mark it as missing.

### README transient fetch error

If README fetch fails due to timeout, rate limit, or temporary upstream error, record `fetch_error` and continue.

This should not fail the whole bootstrap because README tracking is an add-on to the primary rule generation path.

Markdown output should distinguish `fetch_error` from `missing`.

## Testing Strategy

### Unit tests

Add tests for:

- deriving `README.md` URLs from resolved upstream rule URLs
- snapshot path generation per service and source
- correct status handling for `ok`, `missing`, and `fetch_error`

### Docs rendering tests

Add tests that confirm:

- `docs/services.md` links to detail pages
- a service detail page includes rule file links and README links
- multi-source services render multiple upstream blocks
- missing README status is visible in the output

### Integration-style tests with fixtures

Use fixture content instead of live network calls for README tests.

The goal is to keep CI deterministic. GitHub Actions should validate the behavior of the code, not the uptime of upstream repositories.

## Workflow Integration

The existing workflows should stay simple:

- `validate.yml` continues to run `bootstrap` to prove generated artifacts can be recreated
- `sync-rules.yml` continues to run `bootstrap` and auto-commit changes under `docs/` and `dist/`

This means upstream README text changes can produce normal Git diffs and normal bot commits, just like rule-set changes do today.

## Acceptance Criteria

This design is complete when:

- `bootstrap` produces README snapshots and an upstream docs manifest
- the service index links to detail pages
- at least one multi-source service detail page renders multiple upstream original-text blocks
- a missing README is rendered as an explicit missing state, not inferred text
- CI remains deterministic through fixture-based tests
