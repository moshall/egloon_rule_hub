# Surfboard And Sing-Box Targets Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish every existing service and bundle as Surfboard remote rule sets and sing-box source rule sets.

**Architecture:** Extend target definitions with an optional `source_target` so a derived target can reuse another target's source-selection configuration without duplicating the service catalog. Add dedicated emitters that translate the canonical `Rule(type, value)` model into Surfboard line rules and sing-box version 1 JSON while omitting rule types that cannot be represented safely.

**Tech Stack:** Python 3.12, PyYAML, standard-library `unittest`, JSON, GitHub Actions.

---

### Task 1: Lock Target Format Behavior

**Files:**
- Create: `tests/test_target_emitters.py`
- Create: `src/egloon_rule_hub/emitters/surfboard.py`
- Create: `src/egloon_rule_hub/emitters/singbox.py`

**Step 1: Write failing emitter tests**

Cover Surfboard aliases and supported-rule filtering. Cover sing-box version 1 JSON, one headless rule per field, CIDR flag cleanup, and unsupported-rule omission.

**Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_target_emitters -v`

Expected: FAIL because the two emitters do not exist.

**Step 3: Implement the emitters**

Create `render_surfboard_rules(rules)` and `render_singbox_rule_set(rules)` with deterministic output.

**Step 4: Run tests and verify success**

Run: `python -m unittest tests.test_target_emitters -v`

Expected: all emitter tests pass.

### Task 2: Add Derived Target Selection

**Files:**
- Create: `tests/test_derived_targets.py`
- Modify: `src/egloon_rule_hub/model/catalog.py`
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `catalog/targets.yaml`
- Modify: `catalog/services.yaml`
- Modify: `catalog/bundles.yaml`

**Step 1: Write failing derived-target tests**

Verify `source_target` validation, reuse of Shadowrocket source selection, conversion metadata, and inclusion of both new targets in every service and bundle.

**Step 2: Run tests and verify failure**

Run: `python -m unittest tests.test_derived_targets -v`

Expected: FAIL because `TargetDef.source_target` and the new catalog targets do not exist.

**Step 3: Implement target inheritance**

Resolve a missing target-specific source configuration through `source_target`, retain the derived target name for publication, and record the actual upstream native target in conversion metadata.

**Step 4: Register new targets**

Add `surfboard` and `singbox` to target definitions and shared service/bundle target anchors.

**Step 5: Run tests and verify success**

Run: `python -m unittest tests.test_derived_targets -v`

Expected: all derived-target tests pass.

### Task 3: Integrate Renderers And Documentation

**Files:**
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/cli.py`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `pyproject.toml`
- Modify: `.github/workflows/validate.yml`

**Step 1: Add failing rendering integration assertions**

Verify output extensions, target display directories, target manifest metadata, and documented usage examples.

**Step 2: Run tests and verify failure**

Run: `python -m unittest discover -s tests -v`

Expected: FAIL until renderer registration and display mappings exist.

**Step 3: Wire renderers and manifests**

Register `Surfboard` with `.list`, `SingBox` with `.json`, add display names, and expose `source_target` in `targets.json`.

**Step 4: Update documentation and CI**

Document client-specific usage and unsupported mappings. Add unit tests to the validation workflow.

**Step 5: Run all tests**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass.

### Task 4: Generate And Verify Published Artifacts

**Files:**
- Generate: `Rule/Surfboard/**`
- Generate: `Rule/SingBox/**`
- Generate: `dist/manifests/*.json`
- Generate: `ATTRIBUTION.md`

**Step 1: Validate the catalog**

Run: `python -m egloon_rule_hub validate-catalog`

Expected: catalog reports seven enabled targets.

**Step 2: Run a complete bootstrap**

Run: `python -m egloon_rule_hub bootstrap`

Expected: command exits successfully and generates both target trees for services and bundles.

**Step 3: Verify generated formats**

Parse every `Rule/SingBox/**/*.json`, confirm version 1 and non-empty rule arrays, and confirm Surfboard files contain only documented rule types.

**Step 4: Re-run tests and bootstrap**

Run both unit tests and bootstrap again to prove deterministic regeneration.

### Task 5: Commit And Push

**Files:**
- Stage all intentional source, test, documentation, manifest, and generated target changes.

**Step 1: Review the complete diff**

Run: `git status --short` and `git diff --stat`.

**Step 2: Commit**

Run: `git commit -m "feat: add Surfboard and sing-box rule targets"`

**Step 3: Push**

Run: `git push origin HEAD:main`

**Step 4: Verify remote state**

Run: `git ls-remote origin refs/heads/main` and compare it with the local commit.
