# Target-Native Fallback And Loon LSR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current service-wide merged source model with strict target-first family selection (`native -> shadowrocket -> clash`) and make Loon publish as `.lsr` by default with inherited section comments when available.

**Architecture:** Reshape the catalog so each service declares source families per output target, then build one selected artifact per `service + target` instead of one universal merged service rule set. Carry selected-family metadata through build, manifests, and README rendering, and add a dedicated Loon `.lsr` publishing path that inherits headings from the selected family source text or falls back to a single file header.

**Tech Stack:** Python 3.12, setuptools package layout, `unittest`, YAML/Markdown emitters, GitHub Actions bootstrap workflow

---

## File Structure

### Reference inputs

- Spec: `docs/superpowers/specs/2026-04-11-target-native-fallback-design.md`
- Existing publish layout spec: `docs/superpowers/specs/2026-04-11-rule-directory-publishing-design.md`

### Files to create

- `src/egloon_rule_hub/model/publish.py`
  - Hold target-specific build metadata such as selected family, selected source entries, conversion path, publish mode, and raw source texts needed by the Loon `.lsr` path.
- `src/egloon_rule_hub/emitters/loon_lsr.py`
  - Keep `.lsr` formatting and heading inheritance logic out of the generic `build.py` path.

### Files to modify

- `catalog/targets.yaml`
  - Add target options needed for Loon publish mode.
- `catalog/services.yaml`
  - Replace flat `targets + sources` service schema with target-first source-family schema.
- `src/egloon_rule_hub/model/catalog.py`
  - Add nested service target config, family validation, default fallback order loading, and target publish options.
- `src/egloon_rule_hub/build.py`
  - Implement strict family selection, target-specific artifact building, bundle merge-by-target, and Loon publish-mode dispatch.
- `src/egloon_rule_hub/parsers/loon.py`
  - Preserve the flat parser and add section extraction helpers for `.lsr` heading inheritance from list-like source text.
- `src/egloon_rule_hub/emitters/loon.py`
  - Narrow to plain `.list` rendering and delegate `.lsr` rendering to the new emitter module.
- `src/egloon_rule_hub/upstream_docs/build.py`
  - Emit selected-family metadata rather than target-guessing metadata.
- `src/egloon_rule_hub/docs/render.py`
  - Render README files from selected-family facts, include publish mode, and stop listing unused fallback families.
- `src/egloon_rule_hub/cli.py`
  - Render manifests from the new target-specific build graph and keep bootstrap orchestration aligned.
- `README.md`
  - Update published examples from `OpenAI.list` to `OpenAI.lsr` for Loon default output and document target-first source selection.
- `docs/usage.md`
  - Update raw URL examples and describe Loon publish mode.
- `tests/test_build/test_build.py`
  - Cover strict fallback selection, target-specific artifacts, Loon `.lsr`, and bundle behavior.
- `tests/test_cli/test_cli.py`
  - Update minimal fixture catalog and bootstrap expectations to the new schema and Loon `.lsr` default.
- `tests/test_normalize/test_catalog.py`
  - Cover new catalog loading, selected-family-only README rendering, and Loon publish-mode wording.
- `tests/test_upstream_docs/test_build.py`
  - Cover selected-family metadata in the upstream docs manifest.
- `tests/test_emitters/test_emitters.py`
  - Cover plain `.list` rendering plus `.lsr` rendering entrypoints.
- `tests/test_parsers/test_parsers.py`
  - Cover Loon section extraction and fallback behavior.

---

### Task 1: Redesign The Catalog Model Around Target-First Source Families

**Files:**
- Modify: `catalog/targets.yaml`
- Modify: `catalog/services.yaml`
- Modify: `src/egloon_rule_hub/model/catalog.py`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write failing tests for the new catalog schema**

Add tests that load a minimal catalog shaped like:

```yaml
targets:
  loon:
    enabled: true
    file_ext: lsr
    publish_mode: lsr

services:
  OpenAI:
    enabled: true
    outputs: [loon, clash, egern]
    target_sources:
      loon:
        native:
          - source: sample
            url: https://example.com/rule/Loon/OpenAI/OpenAI.list
            format: loon_list
      egern:
        native: []
        shadowrocket: []
        clash:
          - source: sample
            url: https://example.com/rule/Clash/OpenAI/OpenAI.yaml
            format: clash_yaml
```

Assert that:

- `catalog.services["OpenAI"]` exposes output targets and target-scoped families
- `catalog.targets["loon"]` exposes `publish_mode == "lsr"`
- unknown family keys raise validation errors

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_normalize.test_catalog.CatalogTests tests.test_cli.test_cli.BootstrapCLITest -v`

Expected:
- FAIL because `model/catalog.py` still expects flat `targets` and `sources`
- FAIL because the CLI fixture writer still emits the old catalog shape

- [ ] **Step 3: Implement the new catalog dataclasses and loader**

Update `src/egloon_rule_hub/model/catalog.py` to introduce explicit nested config, for example:

```python
@dataclass(slots=True)
class TargetSourceGroup:
    family: str
    sources: list[SourceRef]

@dataclass(slots=True)
class ServiceTargetDef:
    target: str
    fallback_order: list[str]
    families: dict[str, list[SourceRef]]

@dataclass(slots=True)
class ServiceDef:
    name: str
    enabled: bool
    outputs: list[str]
    target_sources: dict[str, ServiceTargetDef]
    override: str | None = None
    notes: str = ""
```

Also update `TargetDef` to carry `publish_mode` for Loon:

```python
@dataclass(slots=True)
class TargetDef:
    name: str
    enabled: bool
    file_ext: str
    publish_mode: str | None = None
```

Validation rules must include:

- allowed family keys are `native`, `shadowrocket`, `clash`
- every output target exists
- every source ref has `path` or `url`
- custom fallback order only references allowed family keys

In the same task, migrate the real `catalog/services.yaml` and `catalog/targets.yaml` to the new schema so `load_catalog(root)` still passes against the repository itself.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_normalize.test_catalog.CatalogTests tests.test_cli.test_cli.BootstrapCLITest -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add catalog/targets.yaml catalog/services.yaml src/egloon_rule_hub/model/catalog.py tests/test_normalize/test_catalog.py tests/test_cli/test_cli.py
git commit -m "feat: load target-first source family catalog"
```

### Task 2: Build Strict Selected-Family Artifacts Per Service And Target

**Files:**
- Create: `src/egloon_rule_hub/model/publish.py`
- Modify: `src/egloon_rule_hub/build.py`
- Test: `tests/test_build/test_build.py`

- [ ] **Step 1: Write failing tests for strict family selection**

Add targeted build tests that assert:

- `native` wins and blocks lower families
- `shadowrocket` wins when native is empty
- `clash` wins when native and shadowrocket are empty
- lower-priority families are not merged after a higher family is selected
- bundles merge per-target selected artifacts, not universal service rules

Use fixtures that make the wrong selection obvious, for example:

```python
native_loon = "# > OpenAI\nDOMAIN,openai.com\n"
shadowrocket = "DOMAIN,shadowrocket-only.example\n"
clash_yaml = "payload:\n  - DOMAIN,clash-only.example\n"
```

Then assert the emitted target artifact contains only the selected family’s rules.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_build.test_build -v`

Expected:
- FAIL because `build.py` still builds one service-wide merged rule list
- FAIL because bundle output still merges the old `dict[str, list[Rule]]`

- [ ] **Step 3: Implement selected-target build records and selection logic**

Create `src/egloon_rule_hub/model/publish.py` with dataclasses such as:

```python
@dataclass(slots=True)
class SelectedSourceEntry:
    source_name: str
    family: str
    format: str
    url: str
    priority: int
    raw_text: str

@dataclass(slots=True)
class TargetArtifact:
    service: str
    target: str
    selected_family: str
    selected_native_target: str
    publish_mode: str | None
    is_native: bool
    is_converted: bool
    conversion_path: str | None
    rules: list[Rule]
    selected_entries: list[SelectedSourceEntry]
```

Update `build.py` so it exposes a target-specific build graph, for example:

```python
dict[str, dict[str, TargetArtifact]]
```

Implementation requirements:

- choose exactly one family per `service + target`
- merge only entries from that family
- keep selected raw text for downstream `.lsr` rendering and docs
- derive `selected_native_target` from selected family plus output target
- compute bundle outputs by merging `artifact.rules` for the bundle target only

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_build.test_build -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/model/publish.py src/egloon_rule_hub/build.py tests/test_build/test_build.py
git commit -m "feat: build target-specific artifacts by selected family"
```

### Task 3: Add Loon Publish Modes And Structured `.lsr` Rendering

**Files:**
- Create: `src/egloon_rule_hub/emitters/loon_lsr.py`
- Modify: `src/egloon_rule_hub/parsers/loon.py`
- Modify: `src/egloon_rule_hub/emitters/loon.py`
- Modify: `src/egloon_rule_hub/build.py`
- Test: `tests/test_parsers/test_parsers.py`
- Test: `tests/test_emitters/test_emitters.py`
- Test: `tests/test_build/test_build.py`

- [ ] **Step 1: Write failing parser and emitter tests for `.lsr`**

Add parser tests for section extraction from list-like source text:

```python
text = "# Apple Intelligence\nDOMAIN,ai.apple.com\n\n# > Claude\nDOMAIN-SUFFIX,claude.ai\n"
sections = extract_loon_sections(text)
assert [section.heading for section in sections] == ["Apple Intelligence", "> Claude"]
```

Add emitter tests that assert:

- `.lsr` preserves inherited headings
- `.lsr` falls back to `# > OpenAI` when no headings are available
- `.list` remains a plain newline-joined file

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_parsers.test_parsers tests.test_emitters.test_emitters -v`

Expected:
- FAIL because `parsers/loon.py` currently drops all comments
- FAIL because there is no `.lsr` emitter path

- [ ] **Step 3: Implement `.lsr` structure extraction and rendering**

Add `src/egloon_rule_hub/emitters/loon_lsr.py` with a narrow API, for example:

```python
def render_loon_lsr(service_name: str, rules: list[Rule], source_texts: list[str]) -> str:
    ...
```

Implementation rules:

- inspect only the selected family source texts
- inherit heading/comment groups from parseable list-like input
- preserve rule order within inherited groups where possible
- place unmatched rules after inherited groups
- if no usable groups are found, render:

```text
# > OpenAI
DOMAIN,openai.com
DOMAIN-SUFFIX,chatgpt.com
```

Keep `src/egloon_rule_hub/emitters/loon.py` focused on `.list` output only.

Update `build.py` to:

- choose `.lsr` or `.list` based on `catalog.targets["loon"].publish_mode`
- use `.lsr` as the default
- mark native Loon + `.lsr` as native publication, not conversion

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_parsers.test_parsers tests.test_emitters.test_emitters tests.test_build.test_build -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/parsers/loon.py src/egloon_rule_hub/emitters/loon.py src/egloon_rule_hub/emitters/loon_lsr.py src/egloon_rule_hub/build.py tests/test_parsers/test_parsers.py tests/test_emitters/test_emitters.py tests/test_build/test_build.py
git commit -m "feat: add loon lsr publish mode"
```

### Task 4: Rewrite Manifests And READMEs Around Selected-Family Provenance

**Files:**
- Modify: `src/egloon_rule_hub/upstream_docs/build.py`
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/cli.py`
- Test: `tests/test_upstream_docs/test_build.py`
- Test: `tests/test_normalize/test_catalog.py`
- Test: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write failing tests for selected-family manifest fields and README wording**

Add manifest assertions like:

```python
self.assertEqual(entry["selected_family"], "clash")
self.assertEqual(entry["selected_native_target"], "clash")
self.assertEqual(entry["publish_mode"], "lsr")
self.assertEqual(entry["conversion_path"], "Clash -> Egern")
```

Add README assertions like:

```python
self.assertIn("Selected source family: `clash`", readme)
self.assertIn("Conversion path: `Clash -> Egern`", readme)
self.assertNotIn("shadowrocket", readme)
```

For Loon native `.lsr`, assert:

```python
self.assertIn("Publish mode: `lsr`", readme)
self.assertIn("native upstream Loon target", readme)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m unittest tests.test_upstream_docs.test_build tests.test_normalize.test_catalog tests.test_cli.test_cli -v`

Expected:
- FAIL because manifest rows still expose guessed `target` / `is_converted` only
- FAIL because README rendering still prints old generic wording

- [ ] **Step 3: Implement selected-family manifest and README rendering**

Update `src/egloon_rule_hub/upstream_docs/build.py` to emit one row per selected source entry with repeated selected-family metadata:

```python
{
    "target": "egern",
    "target_dir": "Egern",
    "service": "Apple",
    "publish_mode": None,
    "selected_family": "clash",
    "selected_native_target": "clash",
    "is_native": False,
    "is_converted": True,
    "conversion_path": "Clash -> Egern",
    ...
}
```

Update `src/egloon_rule_hub/docs/render.py` so target README generation:

- lists only the selected family entries
- shows selected family, publish mode, native/converted classification, and conversion path
- fixes the old `Target: egern` ambiguity by rendering the upstream native target explicitly
- prints `Publish mode: lsr` for Loon artifacts

Update `src/egloon_rule_hub/cli.py` manifest rendering so `services.json` reflects the new service schema, for example:

- `outputs`
- `configured_families`
- target publish mode where relevant

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m unittest tests.test_upstream_docs.test_build tests.test_normalize.test_catalog tests.test_cli.test_cli -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/upstream_docs/build.py src/egloon_rule_hub/docs/render.py src/egloon_rule_hub/cli.py tests/test_upstream_docs/test_build.py tests/test_normalize/test_catalog.py tests/test_cli/test_cli.py
git commit -m "feat: render selected-family provenance in docs"
```

### Task 5: Update Top-Level Documentation And Examples

**Files:**
- Modify: `README.md`
- Modify: `docs/usage.md`
- Test: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write a focused regression test for real Loon output naming**

Extend `tests/test_cli/test_cli.py` bootstrap fixture coverage so a minimal Loon target with default settings expects:

```python
root / "Rule" / "Loon" / "OpenAI" / "OpenAI.lsr"
```

and not `OpenAI.list`.

- [ ] **Step 2: Run test to verify it fails against the real catalog/docs expectations**
- [ ] **Step 2: Run test to verify it fails against the documentation expectations**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli.BootstrapCLITest.test_bootstrap_generates_rule_and_readme_files -v`

Expected: FAIL until the fixture and public docs/examples align on `.lsr`

- [ ] **Step 3: Update top-level docs and examples**

Update `README.md` and `docs/usage.md` examples from:

```text
Rule/Loon/OpenAI/OpenAI.list
```

to:

```text
Rule/Loon/OpenAI/OpenAI.lsr
```

Also document:

- strict fallback order
- native/direct vs converted behavior
- Loon publish-mode override path

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `.venv/bin/python -m unittest tests.test_cli.test_cli.BootstrapCLITest.test_bootstrap_generates_rule_and_readme_files -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/usage.md tests/test_cli/test_cli.py
git commit -m "docs: update examples for loon lsr publishing"
```

### Task 6: Refresh Generated Artifacts And Run Full Verification

**Files:**
- Modify: generated `Rule/**`
- Modify: generated `docs/services.md`
- Modify: generated `dist/manifests/*.json`

- [ ] **Step 1: Run bootstrap on the real repository**

Run: `./.venv/bin/python -m egloon_rule_hub bootstrap`

Expected:
- `Catalog OK: ...`
- `Bootstrap complete`

- [ ] **Step 2: Verify representative generated outputs**

Run:

```bash
test -f Rule/Loon/OpenAI/OpenAI.lsr
test -f Rule/Egern/OpenAI/README.md
test -f dist/manifests/upstream_docs.json
```

Expected: exit `0`

Spot-check:

- `Rule/Loon/OpenAI/OpenAI.lsr` contains either inherited headings or `# > OpenAI`
- `Rule/Egern/Apple/README.md` lists one selected family only

- [ ] **Step 3: Run the full test suite**

Run: `./.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -t . -v`

Expected:
- all tests pass
- no stale assertions for `.list` default Loon output remain

- [ ] **Step 4: Stage generated outputs and final code**

```bash
git add Rule docs dist src catalog tests README.md
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: implement target-native fallback publishing"
```
