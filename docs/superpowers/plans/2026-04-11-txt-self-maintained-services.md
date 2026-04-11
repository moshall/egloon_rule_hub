# TXT Self-Maintained Services Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-discover `Source/TXT/*.txt`, treat each file as a self-maintained service, and publish daily rule artifacts plus self-maintained READMEs for `Egern`, `Loon`, `Clash`, `QuanX`, and `Shadowrocket`.

**Architecture:** Add a TXT discovery/parser layer that scans `Source/TXT/*.txt`, normalizes relaxed shorthand into internal `Rule` objects, and injects discovered services into the runtime catalog with explicit self-maintained origin metadata. Reuse the existing target-artifact build and emitter pipeline by short-circuiting TXT-backed services to canonical local rules, then update README rendering to branch on service origin rather than assuming every published target comes from upstream README manifests.

**Tech Stack:** Python 3.12, setuptools package layout, `unittest`, YAML/Markdown emitters, GitHub Actions bootstrap workflow

---

## File Structure

### Reference inputs

- Spec: `docs/superpowers/specs/2026-04-11-txt-self-maintained-services-design.md`
- Existing TXT sources: `Source/TXT/Feishu.txt`, `Source/TXT/IyfTv`

### Files to create

- `src/egloon_rule_hub/txt_sources/manual.py`
  - Discover `Source/TXT/*.txt`, parse relaxed TXT syntax, extract metadata comments, and return per-service snapshots with normalized rules.
- `tests/test_txt_sources/test_manual.py`
  - Cover TXT discovery, shorthand parsing, metadata extraction, ordering, and dedupe behavior.

### Files to modify

- `src/egloon_rule_hub/txt_sources/__init__.py`
  - Re-export manual discovery helpers alongside existing refresh helpers.
- `src/egloon_rule_hub/model/catalog.py`
  - Add self-maintained origin metadata to services and merge discovered TXT services into the runtime catalog.
- `src/egloon_rule_hub/build.py`
  - Build target artifacts directly from parsed TXT rules, skip upstream-family selection for self-maintained services, and preserve previous outputs on TXT parse failures.
- `src/egloon_rule_hub/docs/render.py`
  - Generate self-maintained READMEs from service origin metadata while retaining upstream README behavior for catalog-backed services.
- `src/egloon_rule_hub/cli.py`
  - Pass target-artifact context into doc rendering so README generation can work for TXT-backed services too.
- `tests/test_build/test_build.py`
  - Cover TXT-backed target generation and failed-parse preservation behavior.
- `tests/test_normalize/test_catalog.py`
  - Cover TXT discovery integration into `load_catalog(root)` and service metadata shape.
- `tests/test_cli/test_cli.py`
  - Cover bootstrap/render-docs expectations for self-maintained services and keep workflow expectations aligned.
- `README.md`
  - Document self-maintained TXT services as a first-class source path.
- `Source/TXT/README.md`
  - Document `.txt`-only discovery and relaxed TXT syntax.
- `Source/TXT/IyfTv`
  - Remove or rename as part of filename normalization.
- `Source/TXT/IyfTv.txt`
  - Normalized filename for the existing IyfTv manual rule source.

---

### Task 1: Add TXT Discovery And Relaxed Parsing

**Files:**
- Create: `src/egloon_rule_hub/txt_sources/manual.py`
- Create: `tests/test_txt_sources/test_manual.py`
- Modify: `src/egloon_rule_hub/txt_sources/__init__.py`
- Modify: `Source/TXT/IyfTv`
- Create: `Source/TXT/IyfTv.txt`
- Modify: `Source/TXT/README.md`

- [ ] **Step 1: Write failing tests for TXT discovery and parsing**

Add tests that create a temporary `Source/TXT/` tree with:

```text
Source/TXT/IyfTv.txt
Source/TXT/Feishu.txt
Source/TXT/ignore.me
```

Use TXT content like:

```text
# just a comment
# @source_url: https://example.com/original
# @generated_by: unit-test
example.com
1.2.3.0/24
DOMAIN,api.example.com
DOMAIN-SUFFIX,cdn.example.com
```

Assert that:

- only `.txt` files are discovered
- `IyfTv.txt` maps to service name `IyfTv`
- metadata extracts `source_url` and `generated_by`
- `example.com` becomes `DOMAIN-SUFFIX,example.com`
- `1.2.3.0/24` becomes `IP-CIDR,1.2.3.0/24`
- rule order is preserved after normalization
- duplicate normalized rules are removed

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.test_txt_sources.test_manual -v`

Expected:
- FAIL because `txt_sources/manual.py` does not exist yet
- FAIL because no TXT discovery/parser API is available from `txt_sources/__init__.py`

- [ ] **Step 3: Implement manual TXT discovery and parser**

Create `src/egloon_rule_hub/txt_sources/manual.py` with focused dataclasses and helpers, for example:

```python
@dataclass(slots=True)
class TxtServiceSnapshot:
    service_name: str
    source_path: Path
    metadata: dict[str, str]
    rules: list[Rule]

def discover_txt_services(root: Path) -> list[TxtServiceSnapshot]:
    ...

def parse_txt_service_text(text: str) -> tuple[dict[str, str], list[Rule]]:
    ...
```

Implementation requirements:

- scan only `Source/TXT/*.txt`
- parse `# @key: value` metadata comments
- support explicit rule lines through the existing list parser path when possible
- support relaxed shorthand for bare domains and CIDRs
- ignore regular comments and blank lines
- dedupe normalized rules while preserving order

Also normalize the repository fixture:

- copy `Source/TXT/IyfTv` to `Source/TXT/IyfTv.txt`
- remove the legacy no-extension file
- update `Source/TXT/README.md` to state `.txt`-only discovery and relaxed syntax

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m unittest tests.test_txt_sources.test_manual tests.test_txt_sources.test_feishu -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/txt_sources/__init__.py src/egloon_rule_hub/txt_sources/manual.py tests/test_txt_sources/test_manual.py tests/test_txt_sources/test_feishu.py Source/TXT/README.md Source/TXT/IyfTv.txt
git rm --ignore-unmatch Source/TXT/IyfTv
git commit -m "feat: add manual txt discovery and parsing"
```

### Task 2: Inject TXT Services Into The Runtime Catalog

**Files:**
- Modify: `src/egloon_rule_hub/model/catalog.py`
- Modify: `tests/test_normalize/test_catalog.py`

- [ ] **Step 1: Write failing tests for catalog injection**

Add tests that build a temporary repository root with:

- a minimal static `catalog/` set
- `Source/TXT/IyfTv.txt`
- `Source/TXT/Feishu.txt`

Assert that `load_catalog(root)` returns:

- `catalog.services["IyfTv"]` and `catalog.services["Feishu"]`
- `catalog.services["IyfTv"].targets == ["egern", "loon", "clash", "quanx", "shadowrocket"]`
- an origin marker that clearly identifies the service as self-maintained
- a source path that points to `Source/TXT/<Service>.txt`
- metadata such as `source_url` when present
- a catalog-owned parsed rule payload that later build steps can consume without refetching

Suggested assertions:

```python
self.assertEqual(catalog.services["Feishu"].origin.kind, "self_maintained")
self.assertEqual(catalog.services["Feishu"].origin.source_path, "Source/TXT/Feishu.txt")
self.assertEqual(catalog.services["Feishu"].origin.source_url, "https://www.feishu.cn/...")
self.assertIn("Feishu", catalog.self_maintained_rules)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.test_normalize.test_catalog.CatalogTests -v`

Expected:
- FAIL because `load_catalog(root)` only reads YAML catalog entries
- FAIL because `ServiceDef` and `Catalog` do not yet expose self-maintained origin metadata or parsed-rule storage

- [ ] **Step 3: Implement runtime TXT service injection**

Extend `src/egloon_rule_hub/model/catalog.py` with explicit origin metadata, for example:

```python
@dataclass(slots=True)
class ServiceOrigin:
    kind: str = "upstream"
    source_path: str | None = None
    source_url: str | None = None
    source_note: str | None = None
    generated_by: str | None = None
```

Update `ServiceDef` and `Catalog` so the runtime model can hold:

- `origin: ServiceOrigin`
- `self_maintained_rules: dict[str, list[Rule]]`
- `self_maintained_failures: dict[str, str]`

Then update `load_catalog(root)` to:

- load static YAML catalog exactly as before
- call `discover_txt_services(root)`
- inject one enabled `ServiceDef` per TXT snapshot
- assign all five targets by default
- store parsed rules in `catalog.self_maintained_rules`

Validation rules must still pass for static catalog services and bundles.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m unittest tests.test_normalize.test_catalog.CatalogTests -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/model/catalog.py tests/test_normalize/test_catalog.py
git commit -m "feat: inject self-maintained txt services into catalog"
```

### Task 3: Build Target Artifacts From TXT Canonical Rules

**Files:**
- Modify: `src/egloon_rule_hub/build.py`
- Modify: `src/egloon_rule_hub/model/publish.py`
- Modify: `tests/test_build/test_build.py`

- [ ] **Step 1: Write failing tests for TXT-backed artifacts and failure isolation**

Add build tests that define a catalog with:

- one upstream-backed service such as `OpenAI`
- one TXT-backed service such as `IyfTv`
- one TXT-backed service parse failure recorded in `catalog.self_maintained_failures`

Assert that:

- `build_all_target_artifacts(catalog)` emits all five targets for `IyfTv`
- each emitted target uses the same canonical rule set with existing emitters
- selected-family behavior for upstream services remains unchanged
- TXT parse failures do not raise and do not delete pre-existing service outputs

Use a minimal TXT canonical rule set like:

```python
catalog.self_maintained_rules["IyfTv"] = [
    Rule("DOMAIN-SUFFIX", "iyf.tv"),
    Rule("DOMAIN-SUFFIX", "yfsp.tv"),
]
```

For failure preservation, pre-create:

- `Rule/Egern/BrokenTxt/BrokenTxt.yaml`
- `Rule/Egern/BrokenTxt/README.md`

Then assert they still exist after rendering when `BrokenTxt` is present in `catalog.self_maintained_failures`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.test_build.test_build -v`

Expected:
- FAIL because `build.py` only knows upstream family selection
- FAIL because no special handling exists for `catalog.self_maintained_rules`

- [ ] **Step 3: Implement TXT-backed artifact generation**

Update `src/egloon_rule_hub/build.py` so target-artifact building does this:

- if `service_name` exists in `catalog.self_maintained_rules`, skip family selection
- create one `TargetArtifact` per enabled target using the canonical parsed rule list
- mark the artifact with metadata that identifies it as self-maintained
- populate `SelectedSourceEntry.raw_text` from the TXT source file for Loon `.lsr` heading support when helpful

Keep `selected_family` stable for compatibility, for example `native`, but do not treat the service as upstream-backed. Add explicit origin flags on the artifact if needed:

```python
artifact.is_self_maintained = True
artifact.source_path = "Source/TXT/IyfTv.txt"
```

Rendering requirements:

- continue publishing to `Rule/<TargetDir>/<Service>/<Service>.<ext>`
- do not prune old files for services listed in `catalog.self_maintained_failures`
- leave bundle behavior unchanged unless TXT services are later explicitly added to bundles

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m unittest tests.test_build.test_build -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/build.py src/egloon_rule_hub/model/publish.py tests/test_build/test_build.py
git commit -m "feat: build target artifacts from txt services"
```

### Task 4: Render Self-Maintained READMEs And Wire Bootstrap End-To-End

**Files:**
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `src/egloon_rule_hub/cli.py`
- Modify: `tests/test_cli/test_cli.py`
- Modify: `tests/test_normalize/test_catalog.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing tests for self-maintained README rendering**

Add tests that bootstrap a repository containing `Source/TXT/Feishu.txt` with:

```text
# @source_url: https://www.feishu.cn/hc/zh-CN/articles/360044683233
# @generated_by: refresh-txt-sources
*.feishu.cn
1.2.3.0/24
```

Assert that:

- `Rule/Egern/Feishu/README.md` exists
- README text says the service is self-maintained
- README text points to `Source/TXT/Feishu.txt`
- README includes the `source_url`
- README does not contain upstream phrases such as `Selected source family` or `Upstream README Sources`

Also add a CLI/bootstrap test that verifies `bootstrap` generates:

- `Rule/Clash/IyfTv/IyfTv.yaml` or `.list` as target-appropriate
- `Rule/Shadowrocket/Feishu/Feishu.list`
- corresponding `README.md` files under each target directory

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli.test_cli tests.test_normalize.test_catalog.ServiceDocsRenderTests -v`

Expected:
- FAIL because README generation currently depends on upstream-doc manifests
- FAIL because `write_markdown_docs` cannot see TXT-backed target artifacts

- [ ] **Step 3: Implement TXT-aware README rendering and CLI handoff**

Reshape `src/egloon_rule_hub/docs/render.py` so target READMEs can be generated from current target artifacts plus optional upstream docs manifest.

Recommended approach:

- change `write_markdown_docs` to accept `target_artifacts`
- derive all live target directories from the artifact graph, not only from `upstream_docs.json`
- branch README markdown:
  - upstream-backed services keep the current upstream README sections
  - self-maintained services render a short template with:
    - service name
    - target name
    - source file path
    - maintenance mode `self-maintained`
    - optional `source_url`, `source_note`, `generated_by`

Update `src/egloon_rule_hub/cli.py` so both `bootstrap` and `render-docs` pass target-artifact context into `write_markdown_docs`.

Update `README.md` to describe self-maintained TXT services as a source path that flows into daily publishing.

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src python3 -m unittest tests.test_cli.test_cli tests.test_normalize.test_catalog.ServiceDocsRenderTests -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/egloon_rule_hub/docs/render.py src/egloon_rule_hub/cli.py tests/test_cli/test_cli.py tests/test_normalize/test_catalog.py README.md
git commit -m "feat: render self-maintained target readmes"
```

### Task 5: Final Verification

**Files:**
- Verify only

- [ ] **Step 1: Run the full test suite**

Run: `PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -t . -v`

Expected: PASS with zero failures

- [ ] **Step 2: Run TXT refresh against the real Feishu source**

Run: `PYTHONPATH=src python3 -m egloon_rule_hub --root . refresh-txt-sources`

Expected:
- exit code `0`
- `Source/TXT/Feishu.txt` updated or reported unchanged

- [ ] **Step 3: Run end-to-end bootstrap**

Run: `PYTHONPATH=src python3 -m egloon_rule_hub --root . bootstrap`

Expected:
- exit code `0`
- `Rule/Egern/Feishu/README.md` exists
- `Rule/Shadowrocket/IyfTv/IyfTv.list` exists

- [ ] **Step 4: Inspect git diff before final handoff**

Run:

```bash
git status --short
git diff --stat
```

Expected:
- only intended TXT-service, README, and test files are changed

- [ ] **Step 5: Commit final integration**

```bash
git add Source/TXT README.md src/ tests/
git commit -m "feat: publish self-maintained txt services"
```
