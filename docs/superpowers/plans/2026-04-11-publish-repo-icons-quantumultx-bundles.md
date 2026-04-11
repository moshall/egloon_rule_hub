# Publish Repo Icons, QuantumultX, and Bundles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `main` into a publish-first rule repository by renaming `QuanX` to `QuantumultX`, expanding the strict-source service catalog and grouped bundles, adding strict upstream icon publication, and removing public development-only folders.

**Architecture:** First migrate the target model and public path surface from `quanx` to `quantumultx` so every downstream builder, renderer, and catalog entry agrees on one target identity. Then expand catalog coverage and bundle definitions, add a dedicated strict icon synchronization pipeline with a separate icon manifest plus per-service README integration, move public metadata away from top-level `docs/`, and only after all verification is done cut the branch over to the minimal publish-repo layout by removing `docs/` and `tests/`.

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
  - Replace every `quanx` target block/output with `quantumultx`, update native source paths to `rule/QuantumultX/...`, and add the newly approved strict-source services.
- `catalog/bundles.yaml`
  - Rename bundle target references to `quantumultx`, expand `ai`, and add `china-bank`.
- `catalog/sources.yaml`
  - Add icon upstream source metadata if the icon sync implementation needs a first-class catalog source entry.
- `src/egloon_rule_hub/model/catalog.py`
  - Update default TXT target allowlist and any target-name assumptions from `quanx` to `quantumultx`.
- `src/egloon_rule_hub/build.py`
  - Teach target rendering, stale-output pruning, and display names about `quantumultx` and `Rule/QuantumultX/`.
- `src/egloon_rule_hub/docs/render.py`
  - Remove dependence on top-level `docs/` as a public output, add icon lines into per-service READMEs, and write root-level attribution instead of `docs/attribution.md`.
- `src/egloon_rule_hub/upstream_docs/build.py`
  - Update target display names and manifest target-dir emission for `QuantumultX`.
- `src/egloon_rule_hub/cli.py`
  - Run icon sync as part of `bootstrap`; keep `render-docs` aligned with the new root/public metadata shape.
- `README.md`
  - Rewrite public branch docs around the publish-first model and `QuantumultX`.
- `.github/workflows/sync-rules.yml`
  - Remove test execution, call the new minimal public refresh path, and stage only public repository content.
- `.github/workflows/validate.yml`
  - Narrow validation to commands that still exist after `tests/` is removed.
- `tests/test_build/test_build.py`
  - Update target rename expectations and stale-prune assertions.
- `tests/test_cli/test_cli.py`
  - Cover icon sync, public staging scope, and root attribution generation.
- `tests/test_normalize/test_catalog.py`
  - Cover `quantumultx` target identity, expanded service catalog load, and bundle membership.
- `tests/test_upstream_docs/test_build.py`
  - Cover `QuantumultX` target-dir naming in upstream README manifest generation.

### Files to remove in the final cleanup task

- `docs/`
- `tests/`

Important:

- Do **not** start the final cleanup task until all previous tasks are complete and verified.
- This plan file and its companion spec file live under `docs/`, so the final cleanup task must be the last implementation task in the session.

---

### Task 1: Rename `QuanX` To `QuantumultX` End-To-End

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
- upstream-doc manifests emit `target_dir == "QuantumultX"` for that target

Use assertions like:

```python
self.assertIn("quantumultx", catalog.targets)
self.assertNotIn("quanx", catalog.targets)
self.assertTrue((root / "Rule" / "QuantumultX" / "OpenAI" / "OpenAI.list").exists())
self.assertFalse((root / "Rule" / "QuanX").exists())
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

### Task 2: Expand Strict-Source Services And Bundle Membership

**Files:**
- Modify: `catalog/services.yaml`
- Modify: `catalog/bundles.yaml`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_build/test_build.py`

- [ ] **Step 1: Write failing tests for service expansion and new bundles**

Add catalog/build tests that assert:

- the new services load into the runtime catalog
- `ChinaASN` is not added
- `ai` includes `BardAI`
- `china-bank` exists and contains `CCB`, `CEB`, `CGB`, `CMB`, `PSBC`
- bundle builds for `quantumultx` emit `dist/bundles/china-bank/quantumultx.list` or the target-appropriate filename

Suggested service assertions:

```python
for name in ["Direct", "Discord", "Disney", "Notion", "BardAI", "Tesla"]:
    self.assertIn(name, catalog.services)
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
  tests.test_build.test_build -v
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

- [ ] **Step 4: Run tests to verify catalog and bundles pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_normalize.test_catalog \
  tests.test_build.test_build -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add catalog/services.yaml catalog/bundles.yaml \
  tests/test_normalize/test_catalog.py tests/test_build/test_build.py
git commit -m "feat: expand strict-source services and bundles"
```

### Task 3: Add Strict Icon Sync And Per-Service Icon Metadata

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

### Task 4: Move Public Metadata Out Of Top-Level `docs/`

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
- `validate.yml` no longer executes `python -m unittest ...`
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

### Task 5: Cut `main` Over To The Minimal Publish Repository

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
