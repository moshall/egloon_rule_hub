# Publish Repo Icons, QuantumultX, and Bundles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `main` into a publish-first rule repository by preserving multi-variant service directories, renaming `QuanX` to `QuantumultX`, expanding the strict-source service catalog and grouped bundles, adding strict upstream icon publication, and removing public development-only folders.

**Architecture:** First fix the core publishing model so one service/target directory can emit multiple variant files instead of collapsing everything to `<Service>.<ext>`. Once variant-aware publishing exists, migrate the target model and public path surface from `quanx` to `quantumultx`, expand catalog coverage and bundle definitions, add bundle README/index files plus strict icon synchronization, move public metadata away from top-level `docs/`, and only after all verification is done cut the branch over to the minimal publish-repo layout by removing `docs/` and `tests/`.

**Tech Stack:** Python 3.12, setuptools package layout, `unittest`, YAML catalogs, markdown/manifest generation, GitHub Actions

---

## File Structure

### Reference inputs

- Spec: `docs/superpowers/specs/2026-04-11-publish-repo-icons-quantumultx-bundles-design.md`
- Current public workflows: `.github/workflows/sync-rules.yml`, `.github/workflows/validate.yml`
- Existing target renderer/docs pipeline: `src/egloon_rule_hub/build.py`, `src/egloon_rule_hub/docs/render.py`, `src/egloon_rule_hub/cli.py`

### Files to create

- `src/egloon_rule_hub/icons/__init__.py`
  - Re-export icon sync helpers used by the CLI/bootstrap path.
- `src/egloon_rule_hub/icons/sync.py`
  - Fetch strict icon candidates from `Keviin560/icon`, write `dist/manifests/icons.json`, and copy matched `icon.png` files into `Rule/<Target>/<Service>/`.
- `tests/test_icons/test_sync.py`
  - Cover strict icon match behavior, missing icon behavior, manifest shape, and stale icon pruning.
- `ATTRIBUTION.md`
  - Root-level public attribution record that replaces `docs/attribution.md` in the final publish branch.

### Files to modify

- `catalog/targets.yaml`
  - Rename target key from `quanx` to `quantumultx`.
- `catalog/services.yaml`
  - Add variant-aware source entries where needed, replace every `quanx` target block/output with `quantumultx`, update native source paths to `rule/QuantumultX/...`, and add the newly approved strict-source services.
- `catalog/bundles.yaml`
  - Rename bundle target references to `quantumultx`, expand `ai`, add `china-bank`, and define bundle README/index expectations against primary service artifacts published under `Rule/<Target>/<BundleDisplayName>/`.
- `catalog/sources.yaml`
  - Add icon upstream source metadata if the icon sync implementation needs a first-class catalog source entry.
- `src/egloon_rule_hub/model/catalog.py`
  - Update default TXT target allowlist, add any variant-aware source metadata fields, and replace target-name assumptions from `quanx` to `quantumultx`.
- `src/egloon_rule_hub/model/publish.py`
  - Extend publication models so one service/target can represent multiple published artifact variants and one primary artifact for bundle merging.
- `src/egloon_rule_hub/build.py`
  - Teach target rendering, stale-output pruning, bundle primary-artifact selection, and display names about variant-aware service directories and bundle publication under `Rule/<Target>/<BundleDisplayName>/`.
- `src/egloon_rule_hub/docs/render.py`
  - Remove dependence on top-level `docs/` as a public output, add variant and icon lines into per-service READMEs, emit bundle README/index files under `Rule/<Target>/<BundleDisplayName>/`, and write root-level attribution instead of `docs/attribution.md`.
- `src/egloon_rule_hub/upstream_docs/build.py`
  - Update target display names and manifest target-dir emission for `QuantumultX`, plus variant-aware upstream README manifest records.
- `src/egloon_rule_hub/cli.py`
  - Run icon sync as part of `bootstrap`; keep `render-docs` aligned with the new root/public metadata shape.
- `README.md`
  - Rewrite public branch docs around the publish-first model and `QuantumultX`.
- `.github/workflows/sync-rules.yml`
  - Remove test execution, call the new minimal public refresh path, and stage only public repository content.
- `.github/workflows/validate.yml`
  - Narrow validation to commands that still exist after `tests/` is removed.
- `tests/test_build/test_build.py`
  - Cover multi-variant service outputs, bundle primary-artifact merges, target rename expectations, and stale-prune assertions.
- `tests/test_cli/test_cli.py`
  - Cover variant-aware bootstrap output, bundle README/index output, icon sync, public staging scope, and root attribution generation.
- `tests/test_normalize/test_catalog.py`
  - Cover variant-aware catalog load, `quantumultx` target identity, expanded service catalog load, and bundle membership.
- `tests/test_upstream_docs/test_build.py`
  - Cover `QuantumultX` target-dir naming and per-variant upstream README manifest generation.

### Files to remove in the final cleanup task

- `docs/`
- `tests/`

Important:

- Do **not** start the final cleanup task until all previous tasks are complete and verified.
- This plan file and its companion spec file live under `docs/`, so the final cleanup task must be the last implementation task in the session.

---

### Task 1: Add Variant-Aware Service Directory Publishing

**Files:**
- Modify: `catalog/services.yaml`
- Modify: `src/egloon_rule_hub/model/catalog.py`
- Modify: `src/egloon_rule_hub/model/publish.py`
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/upstream_docs/build.py`
- Test: `tests/test_build/test_build.py`
- Test: `tests/test_cli/test_cli.py`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_upstream_docs/test_build.py`

- [ ] **Step 1: Write failing tests for multi-variant service directories**

Add or update tests using a real pattern such as `Loon/China` to assert:

- one service/target directory can emit more than one artifact file
- published variant basenames stay aligned to upstream basenames
- `Rule/Loon/China/China.lsr` and `Rule/Loon/China/China_Domain.lsr` can coexist
- service README lists all published variants and their intended usage differences
- service README links each local published variant file
- service README links the upstream source file URL for each variant
- upstream-doc manifest records variant-level rule URLs instead of assuming one file per service/target
- bundle merging still chooses one primary artifact for each service
- an existing single-file service such as `OpenAI` still flows through the same variant-aware runtime path and emits exactly one primary artifact

Use assertions like:

```python
self.assertTrue((root / "Rule" / "Loon" / "China" / "China.lsr").exists())
self.assertTrue((root / "Rule" / "Loon" / "China" / "China_Domain.lsr").exists())
self.assertIn("China_Domain.lsr", readme_text)
self.assertIn("China_Resolve", readme_text)
self.assertIn("./China_Domain.lsr", readme_text)
self.assertIn("rule/Loon/China/China_Domain.list", readme_text)
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_build.test_build \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog \
  tests.test_upstream_docs.test_build -v
```

Expected:

- FAIL because the current model only emits `<Service>.<ext>`
- FAIL because publication models do not represent multiple artifact variants
- FAIL because service README generation assumes one target artifact per service/target

- [ ] **Step 3: Implement variant-aware service publishing**

Make the model change in one coherent slice:

- lock one explicit catalog shape for variants in `catalog/services.yaml`, for example:

```yaml
target_sources:
  loon:
    variants:
      China:
        primary: true
        native:
          - source: blackmatrix7
            path: rule/Loon/China/China.list
            format: loon_list
      China_Domain:
        primary: false
        native:
          - source: blackmatrix7
            path: rule/Loon/China/China_Domain.list
            format: loon_list
      China_Resolve:
        primary: false
        native:
          - source: blackmatrix7
            path: rule/Loon/China/China_Resolve.list
            format: loon_list
```

- extend the catalog/runtime model so a service target can carry multiple publishable upstream file variants when needed
- extend `TargetArtifact` or adjacent publication models to represent:
  - variant basename
  - variant rules
  - whether the variant is the primary artifact for bundle merges
  - variant-level provenance and selected upstream entries
- update rendering so one service directory can publish multiple files
- keep the directory boundary stable:
  - `Rule/<Target>/<Service>/<Variant>.<ext>`
- update README generation to list variant files and usage notes
- update README generation to include local file links and upstream source-file URLs for each variant
- preserve upstream README wording for file differences when available
- update bundle merging so it uses only the primary artifact for each member service

- [ ] **Step 4: Run tests to verify variant-aware publishing passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_build.test_build \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog \
  tests.test_upstream_docs.test_build -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add catalog/services.yaml src/egloon_rule_hub/model/catalog.py \
  src/egloon_rule_hub/model/publish.py src/egloon_rule_hub/build.py \
  src/egloon_rule_hub/docs/render.py src/egloon_rule_hub/upstream_docs/build.py \
  tests/test_build/test_build.py tests/test_cli/test_cli.py \
  tests/test_normalize/test_catalog.py tests/test_upstream_docs/test_build.py
git commit -m "feat: support variant-aware service publishing"
```

### Task 2: Rename `QuanX` To `QuantumultX` End-To-End

**Files:**
- Modify: `catalog/targets.yaml`
- Modify: `catalog/services.yaml`
- Modify: `catalog/bundles.yaml`
- Modify: `src/egloon_rule_hub/model/catalog.py`
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/upstream_docs/build.py`
- Modify: `src/egloon_rule_hub/cli.py`
- Test: `tests/test_build/test_build.py`
- Test: `tests/test_cli/test_cli.py`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_upstream_docs/test_build.py`

- [ ] **Step 1: Write failing tests for the new target name and public path**

Add or update tests to assert:

- `load_catalog(root)` exposes `catalog.targets["quantumultx"]`
- self-maintained TXT defaults use `quantumultx`, not `quanx`
- generated directories are `Rule/QuantumultX/<Service>/`
- stale `Rule/QuanX/` directories are pruned during render
- stale bundle files such as `Rule/QuanX/AI/AI.list` are pruned during render
- upstream-doc manifests emit `target_dir == "QuantumultX"` for that target

Use assertions like:

```python
self.assertIn("quantumultx", catalog.targets)
self.assertNotIn("quanx", catalog.targets)
self.assertTrue((root / "Rule" / "QuantumultX" / "OpenAI" / "OpenAI.list").exists())
self.assertFalse((root / "Rule" / "QuanX").exists())
self.assertFalse((root / "Rule" / "QuanX" / "AI" / "AI.list").exists())
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_build.test_build \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog \
  tests.test_upstream_docs.test_build -v
```

Expected:

- FAIL because the runtime still uses `quanx`
- FAIL because docs/build display names still point to `QuanX`
- FAIL because catalog fixtures and TXT defaults still use the old key

- [ ] **Step 3: Implement the `quantumultx` target rename**

Make the rename in one coherent slice:

- change `catalog/targets.yaml` key from `quanx` to `quantumultx`
- replace `quanx` output lists and `target_sources.quanx` blocks in `catalog/services.yaml`
- update native source paths to `rule/QuantumultX/<Service>/<Service>.list`
- replace bundle target references with `quantumultx`
- update `DEFAULT_TXT_TARGETS` in `src/egloon_rule_hub/model/catalog.py`
- update `TARGET_RENDERERS`, `TARGET_DISPLAY_NAMES`, and stale-prune logic in `src/egloon_rule_hub/build.py`
- update `TARGET_DISPLAY_NAMES`, usage examples, and path rendering in `src/egloon_rule_hub/docs/render.py`
- update target-dir labeling in `src/egloon_rule_hub/upstream_docs/build.py`
- prune stale bundle outputs that still use the old `QuanX` directory and filename pattern
- keep the existing parser/emitter modules (`parsers/quanx.py`, `emitters/quanx.py`) as implementation details; do not rename them yet unless the code requires it

- [ ] **Step 4: Run tests to verify the rename passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_build.test_build \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog \
  tests.test_upstream_docs.test_build -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add catalog/targets.yaml catalog/services.yaml catalog/bundles.yaml \
  src/egloon_rule_hub/model/catalog.py src/egloon_rule_hub/build.py \
  src/egloon_rule_hub/docs/render.py src/egloon_rule_hub/upstream_docs/build.py \
  src/egloon_rule_hub/cli.py tests/test_build/test_build.py \
  tests/test_cli/test_cli.py tests/test_normalize/test_catalog.py \
  tests/test_upstream_docs/test_build.py
git commit -m "feat: rename quanx target to quantumultx"
```

### Task 3: Expand Strict-Source Services, Bundle Membership, And Bundle Indexes

**Files:**
- Modify: `catalog/services.yaml`
- Modify: `catalog/bundles.yaml`
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_build/test_build.py`
- Test: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write failing tests for service expansion and new bundles**

Add catalog/build tests that assert:

- the new services load into the runtime catalog
- already supported strict-source services such as `ChinaDNS` and `ChinaIPs` remain present
- `ChinaASN` is not added
- `ai` includes `BardAI`
- `china-bank` exists and contains `CCB`, `CEB`, `CGB`, `CMB`, `PSBC`
- bundle builds publish merged files under `Rule/<Target>/<BundleDisplayName>/`, for example `Rule/QuantumultX/AI/AI.list`
- each published bundle directory emits `README.md`
- bundle README links to member service directories under `Rule/<Target>/<Service>/`
- when a member service has additional variants, bundle README explains which primary artifact is merged and which extra variants remain available for manual control

Suggested service assertions:

```python
for name in ["Direct", "Discord", "Disney", "Notion", "BardAI", "Tesla"]:
    self.assertIn(name, catalog.services)
self.assertIn("ChinaDNS", catalog.services)
self.assertIn("ChinaIPs", catalog.services)
self.assertNotIn("ChinaASN", catalog.services)
self.assertEqual(
    catalog.bundles["china-bank"].services,
    ["CCB", "CEB", "CGB", "CMB", "PSBC"],
)
```

- [ ] **Step 2: Run targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_normalize.test_catalog \
  tests.test_build.test_build \
  tests.test_cli.test_cli -v
```

Expected:

- FAIL because the requested services are not yet in `catalog/services.yaml`
- FAIL because `china-bank` does not exist and `ai` does not yet include `BardAI`

- [ ] **Step 3: Add the requested strict-source services and bundles**

Update `catalog/services.yaml`:

- add the requested services that have real upstream coverage:
  - `Direct`, `Discord`, `Disney`, `Naver`, `JianGuoYun`, `MEGA`, `Notion`, `OKX`, `TIDAL`, `TestFlight`, `iCloud`, `GoogleFCM`, `ChinaMedia`, `CMB`, `CEB`, `CCB`, `CGB`, `CIBN`, `CNN`, `CNNIC`, `BesTV`, `BardAI`, `BOC`, `BOCOM`, `AppleTV`, `AppleProxy`, `AppleMusic`, `AppleID`, `AppStore`, `Apkpure`, `Android`, `AirChina`, `PSBC`, `Tesla`
- do not add `ChinaASN`
- do not add `X`
- do not add `Grok`
- use `blackmatrix7` native paths for `clash`, `loon`, `shadowrocket`, and `quantumultx`
- keep fallback order `native -> shadowrocket -> clash`

Update `catalog/bundles.yaml`:

- extend `ai` with `BardAI`
- keep `Twitter` in `ai`
- add `china-bank` with the requested bank services

Update bundle publishing:

- keep one merged artifact per target under `Rule/<Target>/<BundleDisplayName>/`
- generate `Rule/<Target>/<BundleDisplayName>/README.md`
- document that merged bundle outputs are deduplicated normalized merges, not raw concatenation
- link each member service directory from the bundle README
- when a service has multiple variants, state which primary artifact participates in the merged bundle and list the additional variants for manual selection
- use public bundle display names in both directory and filename:
  - `Rule/Loon/AI/AI.lsr`
  - `Rule/Clash/ChinaBank/ChinaBank.yaml`

- [ ] **Step 4: Run tests to verify catalog and bundles pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_normalize.test_catalog \
  tests.test_build.test_build \
  tests.test_cli.test_cli -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add catalog/services.yaml catalog/bundles.yaml \
  src/egloon_rule_hub/build.py src/egloon_rule_hub/docs/render.py \
  tests/test_normalize/test_catalog.py tests/test_build/test_build.py \
  tests/test_cli/test_cli.py
git commit -m "feat: expand strict-source services and bundle indexes"
```

### Task 4: Add Strict Icon Sync And Per-Service Icon Metadata

**Files:**
- Create: `src/egloon_rule_hub/icons/__init__.py`
- Create: `src/egloon_rule_hub/icons/sync.py`
- Modify: `src/egloon_rule_hub/cli.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/build.py`
- Test: `tests/test_icons/test_sync.py`
- Test: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write failing tests for strict icon sync**

Create `tests/test_icons/test_sync.py` covering:

- exact-name icon match publishes `icon.png` into every target directory
- missing icon does not publish any guessed file
- `dist/manifests/icons.json` records `matched: true` with `source_path`
- missing icon records `matched: false` with `reason: "strict_match_not_found"`
- icon source fetch failure records `matched: false` with `reason: "icon_sync_source_unavailable"` instead of aborting bootstrap
- stale icons are pruned when a previously matched service no longer matches

Update CLI/doc tests to assert:

- `bootstrap` writes `Rule/Clash/Discord/icon.png` when the upstream icon list contains `Discord.png`
- `Rule/Clash/OpenAI/README.md` contains `Icon: unavailable (strict upstream match not found)` when no exact icon exists

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_icons.test_sync \
  tests.test_cli.test_cli -v
```

Expected:

- FAIL because no icon sync module exists
- FAIL because bootstrap does not yet publish icon assets or icon metadata
- FAIL because service READMEs do not mention icons

- [ ] **Step 3: Implement strict icon sync**

Create `src/egloon_rule_hub/icons/sync.py` with focused helpers, for example:

```python
def build_icon_manifest(catalog: Catalog, fetcher=...) -> dict[str, dict[str, object]]:
    ...

def render_service_icons(
    root: Path,
    target_artifacts: dict[str, dict[str, TargetArtifact]],
    icon_manifest: dict[str, dict[str, object]],
) -> None:
    ...
```

Implementation requirements:

- fetch the upstream file list from `Keviin560/icon/src`
- allow only strict `<Service>.png` matches
- write `dist/manifests/icons.json`
- copy matched files to `Rule/<Target>/<Service>/icon.png`
- prune stale `icon.png` files when a service loses its match or output
- if the upstream icon source is unavailable, do not fail the whole bootstrap; instead mark every unresolved service with `reason: "icon_sync_source_unavailable"` and continue publishing rules/READMEs without icons
- update `src/egloon_rule_hub/cli.py` so `bootstrap` runs icon sync after rule artifacts exist and before README rendering
- update `src/egloon_rule_hub/docs/render.py` so each service README includes exactly one icon line
- keep icon metadata separate from rule-source provenance

- [ ] **Step 4: Run tests to verify icon sync passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_icons.test_sync \
  tests.test_cli.test_cli \
  tests.test_build.test_build -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/icons/__init__.py src/egloon_rule_hub/icons/sync.py \
  src/egloon_rule_hub/cli.py src/egloon_rule_hub/docs/render.py \
  src/egloon_rule_hub/build.py tests/test_icons/test_sync.py \
  tests/test_cli/test_cli.py tests/test_build/test_build.py
git commit -m "feat: publish strict upstream icons"
```

### Task 5: Move Public Metadata Out Of Top-Level `docs/`

**Files:**
- Create: `ATTRIBUTION.md`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `README.md`
- Modify: `tests/test_cli/test_cli.py`
- Modify: `tests/test_normalize/test_catalog.py`
- Modify: `.github/workflows/validate.yml`
- Modify: `.github/workflows/sync-rules.yml`

- [ ] **Step 1: Write failing tests for root attribution and publish-repo workflows**

Update tests to assert:

- `bootstrap` writes root `ATTRIBUTION.md`
- `bootstrap` no longer relies on top-level `docs/services.md`, `docs/sources.md`, or `docs/usage.md` as public outputs
- `bootstrap` keeps writing per-service README files and per-bundle merged files plus `README.md` index files under `Rule/` as public outputs
- `validate.yml` no longer executes `python -m unittest ...`
- `sync-rules.yml` no longer executes `python -m unittest ...`
- `sync-rules.yml` stages only public paths and does not stage `docs` or `tests`

Suggested workflow assertions:

```python
self.assertNotIn("python -m unittest", workflow_text)
self.assertIn("git add Rule dist Source/TXT catalog src README.md ATTRIBUTION.md .github/workflows", workflow_text)
self.assertNotIn("git add Rule docs dist Source/TXT", workflow_text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog -v
```

Expected:

- FAIL because public docs are still written under top-level `docs/`
- FAIL because workflows still run tests and still stage `docs`

- [ ] **Step 3: Implement the publish-first metadata surface**

Update `src/egloon_rule_hub/docs/render.py` so it:

- continues writing per-service README files under `Rule/<Target>/<Service>/`
- continues writing per-bundle merged artifact files and `README.md` files under `Rule/<Target>/<BundleDisplayName>/`
- writes root `ATTRIBUTION.md`
- stops producing `docs/services.md`, `docs/sources.md`, and `docs/usage.md` as required public artifacts
- prunes stale top-level `docs/` outputs if they still exist

Update `README.md`:

- describe `main` as a publish-first branch
- replace `QuanX` references with `QuantumultX`
- explain icon behavior and strict-source behavior

Update workflows:

- `validate.yml` should run lightweight validation only:
  - `python -m egloon_rule_hub validate-catalog`
  - `python -m egloon_rule_hub bootstrap`
- `sync-rules.yml` should refresh TXT, run bootstrap, and stage only:
  - no `python -m unittest ...` step
  - `.github/workflows`
  - `catalog`
  - `src`
  - `Rule`
  - `dist`
  - `Source/TXT`
  - `README.md`
  - `ATTRIBUTION.md`

- [ ] **Step 4: Run tests to verify publish metadata behavior passes**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_cli.test_cli \
  tests.test_normalize.test_catalog -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ATTRIBUTION.md src/egloon_rule_hub/docs/render.py README.md \
  .github/workflows/validate.yml .github/workflows/sync-rules.yml \
  tests/test_cli/test_cli.py tests/test_normalize/test_catalog.py
git commit -m "feat: switch public metadata to publish repo layout"
```

### Task 6: Cut `main` Over To The Minimal Publish Repository

**Files:**
- Remove: `docs/`
- Remove: `tests/`

- [ ] **Step 1: Re-run full verification before deleting development-only folders**

This is the last safe point where the tracked test suite still exists.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -t . -v
PYTHONPATH=src python3 -m egloon_rule_hub validate-catalog
PYTHONPATH=src python3 -m egloon_rule_hub bootstrap
```

Expected:

- all tests PASS
- catalog validation PASS
- bootstrap PASS

- [ ] **Step 2: Remove public `docs/` and `tests/` from tracked git content**

Because this plan file and the approved spec file live under `docs/`, do not do this step until all prior tasks are merged and reviewed.

Run:

```bash
git rm -r docs tests
```

If the implementation produced any new development-only folders during the previous tasks, remove them in the same commit.

- [ ] **Step 3: Run lightweight publish-repo verification after removal**

Run:

```bash
PYTHONPATH=src python3 -m egloon_rule_hub validate-catalog
PYTHONPATH=src python3 -m egloon_rule_hub refresh-txt-sources
PYTHONPATH=src python3 -m egloon_rule_hub bootstrap
git status --short
```

Expected:

- validation PASS
- TXT refresh PASS
- bootstrap PASS
- only intended publish artifacts are modified or staged

- [ ] **Step 4: Commit the public-branch cutover**

```bash
git add -A
git commit -m "chore: trim main to publish repo layout"
```

- [ ] **Step 5: Push and verify workflow assumptions**

Run:

```bash
git push origin main
```

Then verify:

- `validate.yml` still runs with no `tests/` directory present
- `sync-rules.yml` can stage only the publish-repo paths without trying to commit deleted `docs/` or `tests/`

If CI exposes a missing-path assumption, fix it immediately before treating the cutover as complete.
