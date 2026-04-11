# Rule Directory Publishing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace flat per-service publish outputs with `Rule/<Target>/<Service>/` directories and generate target-specific `README.md` files that accurately trace native and converted upstream sources.

**Architecture:** Keep the existing catalog, source resolution, merge, and snapshot flow, but change the publish surface to be target-aware. Rule emission will write into `Rule/` directories, upstream README tracking will remain snapshot-first under `dist/`, and markdown rendering will shift from service detail pages to per-target directory READMEs derived from target-aware manifest data.

**Tech Stack:** Python 3.12, setuptools package layout, `unittest`, YAML/Markdown renderers, GitHub Actions bootstrap workflow

---

## File Structure

### Existing files to modify

- `src/egloon_rule_hub/build.py`
  - Change per-service rule output paths from flat `dist/<target>/<Service>.<ext>` to `Rule/<Target>/<Service>/<Service>.<ext>`.
  - Keep bundle emission under `dist/bundles/` unchanged in this slice.
- `src/egloon_rule_hub/upstream_docs/build.py`
  - Extend manifest generation so upstream README records can be consumed per target/service output, not just per service aggregate.
- `src/egloon_rule_hub/docs/render.py`
  - Replace service-detail-page rendering with target-specific directory `README.md` rendering under `Rule/<Target>/<Service>/README.md`.
  - Update usage/docs text so it reflects the new directory layout.
- `src/egloon_rule_hub/cli.py`
  - Keep bootstrap orchestration intact while ensuring the updated render steps produce the new output surface.
- `README.md`
  - Update published artifact examples to the `Rule/` directory layout.
- `tests/test_build/test_build.py`
  - Update artifact assertions to the new directory structure.
- `tests/test_normalize/test_catalog.py`
  - Replace service-detail-page expectations with target-specific README expectations.
- `tests/test_cli/test_cli.py`
  - Keep bootstrap call expectations accurate if helper signatures or behavior change.

### New files to create

- None required unless target-aware doc rendering becomes clearer with a small helper module. Prefer staying within the current file boundaries unless a focused helper is clearly justified during implementation.

### Existing files to inspect during implementation

- `src/egloon_rule_hub/model/catalog.py`
  - Confirm available target and service metadata needed by README rendering.
- `tests/test_upstream_docs/test_build.py`
  - Reuse existing fixture style for target-aware manifest changes.
- `tests/test_upstream_docs/test_fetch.py`
  - Keep fetch status behavior unchanged while moving the publish surface.

## Task 1: Redirect Rule Artifacts Into `Rule/` Directories

**Files:**
- Modify: `src/egloon_rule_hub/build.py`
- Test: `tests/test_build/test_build.py`

- [ ] **Step 1: Write the failing test for directory-style rule outputs**

Add assertions in `tests/test_build/test_build.py` that expect:

```python
self.assertTrue((self.root / "Rule" / "Loon" / "OpenAI" / "OpenAI.list").exists())
self.assertTrue((self.root / "Rule" / "Clash" / "OpenAI" / "OpenAI.yaml").exists())
self.assertTrue((self.root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml").exists())
```

and remove the old flat `dist/<target>/<Service>.<ext>` assertions for per-service outputs.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_build.test_build.BuildPipelineTests.test_render_rule_artifacts_writes_service_and_bundle_outputs -v`
Expected: FAIL because the code still writes per-service outputs to `dist/<target>/`.

- [ ] **Step 3: Write the minimal implementation for target directory rule outputs**

Update `src/egloon_rule_hub/build.py` so:

- per-service outputs go to `root / "Rule" / <DisplayTarget> / service_name / f"{service_name}.{ext}"`
- target display names are mapped exactly to:

```python
TARGET_OUTPUT_DIRS = {
    "egern": "Egern",
    "loon": "Loon",
    "clash": "Clash",
    "quanx": "QuanX",
    "shadowrocket": "Shadowrocket",
}
```

- bundle outputs remain under `dist/bundles/`

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_build.test_build.BuildPipelineTests.test_render_rule_artifacts_writes_service_and_bundle_outputs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_build/test_build.py src/egloon_rule_hub/build.py
git commit -m "feat: publish service rules in target directories"
```

## Task 2: Make Upstream Docs Manifest Target-Aware

**Files:**
- Modify: `src/egloon_rule_hub/upstream_docs/build.py`
- Test: `tests/test_upstream_docs/test_build.py`

- [ ] **Step 1: Write the failing test for target-aware manifest records**

Add or update tests in `tests/test_upstream_docs/test_build.py` so at least one manifest entry asserts target awareness, for example:

```python
self.assertEqual(entry["target"], "clash")
self.assertEqual(entry["target_dir"], "Clash")
```

and for a converted target fixture path:

```python
self.assertEqual(entry["target"], "egern")
self.assertTrue(entry["is_converted"])
```

The test should also assert the manifest still preserves:

- `rule_url`
- `readme_url`
- `status`
- `snapshot_path`

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_upstream_docs.test_build -v`
Expected: FAIL because the current manifest is service-scoped and lacks target-aware fields.

- [ ] **Step 3: Write the minimal implementation for target-aware manifest records**

Update `src/egloon_rule_hub/upstream_docs/build.py` so manifest records are emitted per target/service output need rather than only per service aggregate.

Each record should include enough data for README rendering, including:

```python
{
    "target": "clash",
    "target_dir": "Clash",
    "service": "OpenAI",
    "source": "blackmatrix7",
    "priority": 100,
    "rule_url": "...",
    "readme_url": "...",
    "status": "ok",
    "snapshot_path": "...",
    "is_converted": False,
}
```

For converted targets such as `egern`, records should still point to the actual upstream-native inputs used for generation and should set `is_converted` to `True`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_upstream_docs.test_build -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_upstream_docs/test_build.py src/egloon_rule_hub/upstream_docs/build.py
git commit -m "feat: make upstream docs manifest target aware"
```

## Task 3: Replace Service Detail Pages With Target Directory READMEs

**Files:**
- Modify: `src/egloon_rule_hub/docs/render.py`
- Test: `tests/test_normalize/test_catalog.py`

- [ ] **Step 1: Write the failing tests for target-specific README generation**

Update `tests/test_normalize/test_catalog.py` so it asserts target README outputs such as:

```python
readme = (root / "Rule" / "Clash" / "OpenAI" / "README.md").read_text(encoding="utf-8")
self.assertIn("# OpenAI for Clash", readme)
self.assertIn("direct upstream target", readme)
```

and:

```python
readme = (root / "Rule" / "Egern" / "OpenAI" / "README.md").read_text(encoding="utf-8")
self.assertIn("generated by egloon_rule_hub", readme)
self.assertIn("not a native upstream Egern artifact", readme)
```

Also add coverage for:

- multiple source blocks in a converted target README
- explicit `upstream README missing`
- original upstream text rendering from snapshot files

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_normalize.test_catalog -v`
Expected: FAIL because the renderer still writes `docs/services/<Service>.md` and is not target-aware.

- [ ] **Step 3: Write the minimal implementation for target directory README rendering**

Update `src/egloon_rule_hub/docs/render.py` so it:

- loads target-aware manifest data
- groups manifest entries by target + service
- writes `README.md` to `Rule/<Target>/<Service>/README.md`
- renders native-target wording when the entry target matches the upstream-native target
- renders converted-target wording for generated targets such as `Egern`
- preserves source-separated original text blocks
- keeps `upstream README missing` and `fetch_error` explicit

The renderer should stop treating `docs/services/<Service>.md` as the primary publish artifact.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_normalize.test_catalog -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_normalize/test_catalog.py src/egloon_rule_hub/docs/render.py
git commit -m "feat: render target directory readmes"
```

## Task 4: Update Usage Docs, Bootstrap Expectations, And Sync Workflow

**Files:**
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `README.md`
- Modify: `.github/workflows/sync-rules.yml`
- Test: `tests/test_cli/test_cli.py`
- Test: `tests/test_normalize/test_catalog.py`

- [ ] **Step 1: Write the failing tests and checks for usage text, bootstrap expectations, and sync workflow coverage**

Add or update assertions so generated usage text references:

```text
Rule/Clash/OpenAI/OpenAI.yaml
Rule/Loon/OpenAI/OpenAI.list
Rule/Egern/OpenAI/OpenAI.yaml
```

and no longer advertises flat per-service `dist/<target>/<Service>.<ext>` paths as the main publish layout.

If bootstrap behavior tests need to observe the new publish surface, add assertions around the generated README or Rule directory presence rather than `docs/services/<Service>.md`.

Also add a workflow-level assertion or direct file expectation check that `sync-rules.yml` stages `Rule` alongside `docs` and `dist`, for example:

```python
workflow = (root / ".github" / "workflows" / "sync-rules.yml").read_text(encoding="utf-8")
self.assertIn("git add Rule docs dist", workflow)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli tests.test_normalize.test_catalog -v`
Expected: FAIL because usage/docs text still points to the old flat layout, old service-detail-page assumptions remain, or the workflow still stages only `docs dist`.

- [ ] **Step 3: Write the minimal implementation for docs, README, and workflow updates**

Update:

- `src/egloon_rule_hub/docs/render.py` usage text and any remaining service-page references
- `README.md` examples and publish-surface descriptions so they show the `Rule/` directory layout
- `.github/workflows/sync-rules.yml` so bot commits stage `Rule`, `docs`, and `dist`

Do not redesign bundles in this step; keep references to bundle outputs under `dist/bundles/`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli tests.test_normalize.test_catalog -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md .github/workflows/sync-rules.yml tests/test_cli/test_cli.py tests/test_normalize/test_catalog.py src/egloon_rule_hub/docs/render.py
git commit -m "docs: update publishing docs for rule directories"
```

## Task 5: Verify Full Bootstrap Output

**Files:**
- Modify: `tests/test_cli/test_cli.py`
- Modify: generated outputs under `Rule/`, `dist/`, and `docs/` as needed

- [ ] **Step 1: Write the failing integration-style test for representative bootstrap outputs**

Add a focused integration-style assertion that after bootstrap, representative files exist:

```python
self.assertTrue((root / "Rule" / "Clash" / "OpenAI" / "OpenAI.yaml").exists())
self.assertTrue((root / "Rule" / "Clash" / "OpenAI" / "README.md").exists())
self.assertTrue((root / "Rule" / "Egern" / "OpenAI" / "OpenAI.yaml").exists())
self.assertTrue((root / "Rule" / "Egern" / "OpenAI" / "README.md").exists())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli -v`
Expected: FAIL until the bootstrap pipeline produces the new output structure end to end.

- [ ] **Step 3: Write the minimal implementation to make bootstrap regenerate the new output surface end to end**

Adjust any remaining orchestration assumptions so one `bootstrap` run regenerates:

- `Rule/<Target>/<Service>/<Service>.<ext>`
- `Rule/<Target>/<Service>/README.md`
- internal manifests and snapshots under `dist/`

Avoid introducing extra user-facing commands in this step.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli/test_cli.py src/egloon_rule_hub/cli.py src/egloon_rule_hub/build.py src/egloon_rule_hub/docs/render.py src/egloon_rule_hub/upstream_docs/build.py
git commit -m "feat: bootstrap rule directory publishing"
```

## Task 6: Final Verification And Generated Artifact Refresh

**Files:**
- Modify: generated files under `Rule/`, `dist/`, and `docs/`

- [ ] **Step 1: Refresh generated outputs**

Run:

```bash
.venv/bin/python -m egloon_rule_hub bootstrap
```

Expected: bootstrap completes and rewrites generated artifacts to the new structure.

- [ ] **Step 2: Run the full test suite**

Run:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -t . -v
```

Expected: PASS with all tests green.

- [ ] **Step 3: Inspect the working tree**

Run:

```bash
git status --short
```

Expected: generated changes only in files relevant to this feature, including `Rule/`, `dist/`, `docs/`, `README.md`, `src/`, and `tests/`.

- [ ] **Step 4: Commit**

```bash
git add README.md Rule dist docs src tests
git commit -m "feat: publish rules in target directories"
```
