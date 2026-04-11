# Upstream README Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic upstream README tracking so each service publishes exact upstream rule links, exact README links, original README text snapshots, and a local summary in generated service detail pages.

**Architecture:** Build a small `upstream_docs` pipeline that derives README URLs from already-resolved rule URLs, snapshots README content into `dist/`, emits a manifest for downstream consumers, and lets the docs renderer build service detail pages from local snapshot data only. Keep rule generation as the primary path, treat README tracking as a non-fatal add-on for missing or transient README fetch failures, and preserve original upstream text in per-entry blocks.

**Tech Stack:** Python 3.12, standard library `urllib` and `json`, existing catalog/resolver pipeline, `unittest`, GitHub Actions bootstrap workflow

---

## File Map

### New files

- `src/egloon_rule_hub/upstream_docs/__init__.py`
  Expose the upstream README tracking package.
- `src/egloon_rule_hub/upstream_docs/fetch.py`
  Derive README URLs from resolved rule URLs and normalize fetch results into `ok`, `missing`, or `fetch_error`.
- `src/egloon_rule_hub/upstream_docs/build.py`
  Iterate catalog source refs, write README snapshots under `dist/upstream-readmes/`, and write `dist/manifests/upstream_docs.json`.
- `tests/test_upstream_docs/__init__.py`
  Test package marker.
- `tests/test_upstream_docs/test_fetch.py`
  Unit tests for README URL derivation and fetch status normalization.
- `tests/test_upstream_docs/test_build.py`
  Unit tests for snapshot writing and manifest output.
- `tests/test_cli/__init__.py`
  Test package marker for CLI coverage.
- `tests/test_cli/test_cli.py`
  CLI bootstrap wiring test to prove upstream README tracking is included in `bootstrap`.

### Modified files

- `src/egloon_rule_hub/cli.py`
  Call upstream README snapshot building during `bootstrap`.
- `src/egloon_rule_hub/docs/render.py`
  Load upstream docs manifest, write service detail pages, and link them from the service index.
- `tests/test_normalize/test_catalog.py`
  Extend docs-render assertions to cover service detail generation from manifest-backed data.
- `README.md`
  Mention the new upstream README tracking capability once the feature ships.

## Design Notes To Preserve During Implementation

- A single service can reference the same `source` more than once today, for example `blackmatrix7` for both Clash and Loon paths. Snapshot storage therefore must use a stable per-source-entry key such as `priority + source + path slug`, not raw `<Service>/<source>` alone, or snapshots will overwrite each other.
- The user-facing page should still read as a service page. The internal key is only for collision-free file paths and manifest records.
- The docs renderer must not make network calls. It should only read `dist/manifests/upstream_docs.json` and snapshot files already produced earlier in the bootstrap flow.

### Task 1: Build README URL derivation and fetch status normalization

**Files:**
- Create: `src/egloon_rule_hub/upstream_docs/__init__.py`
- Create: `src/egloon_rule_hub/upstream_docs/fetch.py`
- Create: `tests/test_upstream_docs/__init__.py`
- Test: `tests/test_upstream_docs/test_fetch.py`

- [ ] **Step 1: Write the failing test**

```python
import unittest
from urllib.error import HTTPError, URLError

from egloon_rule_hub.upstream_docs.fetch import derive_readme_url, fetch_readme


class UpstreamReadmeFetchTests(unittest.TestCase):
    def test_derive_readme_url_from_rule_file_url(self) -> None:
        self.assertEqual(
            derive_readme_url(
                "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.yaml"
            ),
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/README.md",
        )

    def test_fetch_readme_marks_missing_on_404(self) -> None:
        def missing_fetcher(url: str) -> str:
            raise HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        result = fetch_readme(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.yaml",
            fetcher=missing_fetcher,
        )

        self.assertEqual(result.status, "missing")

    def test_fetch_readme_marks_fetch_error_on_transient_failure(self) -> None:
        def broken_fetcher(url: str) -> str:
            raise URLError("temporary network issue")

        result = fetch_readme(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.yaml",
            fetcher=broken_fetcher,
        )

        self.assertEqual(result.status, "fetch_error")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_upstream_docs.test_fetch -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'egloon_rule_hub.upstream_docs'`

- [ ] **Step 3: Write minimal implementation**

```python
from dataclasses import dataclass
from urllib.error import HTTPError, URLError


@dataclass(slots=True)
class ReadmeFetchResult:
    rule_url: str
    readme_url: str
    status: str
    content: str | None
    error: str = ""


def derive_readme_url(rule_url: str) -> str:
    base, _slash, _tail = rule_url.rpartition("/")
    return f"{base}/README.md"


def fetch_readme(rule_url: str, fetcher) -> ReadmeFetchResult:
    readme_url = derive_readme_url(rule_url)
    try:
        return ReadmeFetchResult(
            rule_url=rule_url,
            readme_url=readme_url,
            status="ok",
            content=fetcher(readme_url),
        )
    except HTTPError as exc:
        if exc.code == 404:
            return ReadmeFetchResult(rule_url, readme_url, "missing", None)
        return ReadmeFetchResult(rule_url, readme_url, "fetch_error", None, str(exc))
    except URLError as exc:
        return ReadmeFetchResult(rule_url, readme_url, "fetch_error", None, str(exc))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_upstream_docs.test_fetch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_upstream_docs/__init__.py tests/test_upstream_docs/test_fetch.py src/egloon_rule_hub/upstream_docs/__init__.py src/egloon_rule_hub/upstream_docs/fetch.py
git commit -m "feat: add upstream README fetch primitives"
```

### Task 2: Snapshot README content and emit upstream docs manifest

**Files:**
- Create: `src/egloon_rule_hub/upstream_docs/build.py`
- Test: `tests/test_upstream_docs/test_build.py`
- Modify: `src/egloon_rule_hub/upstream_docs/fetch.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import tempfile
import unittest
from pathlib import Path

from egloon_rule_hub.model.catalog import Catalog, ServiceDef, SourceDef, SourceRef, TargetDef
from egloon_rule_hub.upstream_docs.build import build_upstream_docs


class UpstreamReadmeBuildTests(unittest.TestCase):
    def test_build_upstream_docs_writes_snapshots_and_manifest(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        root = Path(temp_dir.name)

        catalog = Catalog(
            root=root,
            sources={"fixture": SourceDef(name="fixture", kind="remote")},
            targets={"loon": TargetDef(name="loon", enabled=True, file_ext="list")},
            services={
                "OpenAI": ServiceDef(
                    name="OpenAI",
                    enabled=True,
                    targets=["loon"],
                    sources=[
                        SourceRef(
                            source="fixture",
                            url="https://example.com/rule/Loon/OpenAI/OpenAI.list",
                            format="loon_list",
                            priority=90,
                        )
                    ],
                    notes="AI service",
                )
            },
            bundles={},
        )

        def fake_fetcher(url: str) -> str:
            return "# README\\n\\nOriginal upstream text\\n"

        manifest = build_upstream_docs(catalog, fetcher=fake_fetcher)

        snapshot = root / "dist" / "upstream-readmes" / "OpenAI" / "90-fixture-rule-loon-openai-openai-list" / "README.md"
        self.assertTrue(snapshot.exists())
        self.assertEqual(manifest["OpenAI"][0]["status"], "ok")

        payload = json.loads((root / "dist" / "manifests" / "upstream_docs.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["OpenAI"][0]["snapshot_path"], str(snapshot.relative_to(root)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_upstream_docs.test_build -v`
Expected: FAIL with `ImportError` because `build_upstream_docs` does not exist

- [ ] **Step 3: Write minimal implementation**

```python
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from egloon_rule_hub.sources.registry import resolve_source_ref
from egloon_rule_hub.upstream_docs.fetch import fetch_readme


def _entry_key(priority: int, source_name: str, rule_url: str) -> str:
    path_slug = re.sub(r"[^a-z0-9]+", "-", urlparse(rule_url).path.lower()).strip("-")
    return f"{priority}-{source_name}-{path_slug}"


def build_upstream_docs(catalog, fetcher) -> dict[str, list[dict[str, object]]]:
    docs_dir = catalog.root / "dist" / "upstream-readmes"
    manifest_dir = catalog.root / "dist" / "manifests"
    docs_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    manifest = {}
    for service_name, service in catalog.services.items():
        entries = []
        for source_ref in service.sources:
            resolved = resolve_source_ref(catalog.sources[source_ref.source], source_ref)
            result = fetch_readme(resolved.url, fetcher=fetcher)
            entry_key = _entry_key(source_ref.priority, source_ref.source, resolved.url)
            snapshot_path = None
            if result.status == "ok" and result.content is not None:
                snapshot = docs_dir / service_name / entry_key / "README.md"
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                snapshot.write_text(result.content, encoding="utf-8")
                snapshot_path = str(snapshot.relative_to(catalog.root))
            entries.append(
                {
                    "source": source_ref.source,
                    "priority": source_ref.priority,
                    "rule_url": resolved.url,
                    "readme_url": result.readme_url,
                    "status": result.status,
                    "snapshot_path": snapshot_path,
                    "entry_key": entry_key,
                }
            )
        manifest[service_name] = entries

    (manifest_dir / "upstream_docs.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_upstream_docs.test_build -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_upstream_docs/test_build.py src/egloon_rule_hub/upstream_docs/fetch.py src/egloon_rule_hub/upstream_docs/build.py
git commit -m "feat: snapshot upstream readmes and manifest"
```

### Task 3: Render service detail pages from the upstream docs manifest

**Files:**
- Modify: `src/egloon_rule_hub/docs/render.py`
- Modify: `tests/test_normalize/test_catalog.py`

- [ ] **Step 1: Write the failing test**

```python
def test_write_markdown_docs_generates_service_detail_pages(self) -> None:
    temp_dir = tempfile.TemporaryDirectory()
    root = Path(temp_dir.name)
    (root / "dist" / "manifests").mkdir(parents=True, exist_ok=True)
    manifest_dir = root / "dist" / "manifests"
    service_snapshot = root / "dist" / "upstream-readmes" / "OpenAI" / "100-blackmatrix7-rule-clash-openai-openai-yaml" / "README.md"
    service_snapshot.parent.mkdir(parents=True, exist_ok=True)
    service_snapshot.write_text("# OpenAI\\n\\nOriginal upstream text\\n", encoding="utf-8")
    (manifest_dir / "upstream_docs.json").write_text(
        json.dumps(
            {
                "OpenAI": [
                    {
                        "source": "blackmatrix7",
                        "priority": 100,
                        "rule_url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/OpenAI.yaml",
                        "readme_url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OpenAI/README.md",
                        "status": "ok",
                        "snapshot_path": "dist/upstream-readmes/OpenAI/100-blackmatrix7-rule-clash-openai-openai-yaml/README.md",
                        "entry_key": "100-blackmatrix7-rule-clash-openai-openai-yaml",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog = Catalog(
        root=root,
        sources={"blackmatrix7": SourceDef(name="blackmatrix7", kind="blackmatrix7_repo")},
        targets={"loon": TargetDef(name="loon", enabled=True, file_ext="list")},
        services={
            "OpenAI": ServiceDef(
                name="OpenAI",
                enabled=True,
                targets=["loon"],
                sources=[],
                notes="AI service",
            )
        },
        bundles={},
    )
    write_markdown_docs(root, catalog)

    detail = (root / "docs" / "services" / "OpenAI.md").read_text(encoding="utf-8")
    index = (root / "docs" / "services.md").read_text(encoding="utf-8")
    self.assertIn("[OpenAI](services/OpenAI.md)", index)
    self.assertIn("Original upstream text", detail)
    self.assertIn("README.md", detail)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_normalize.test_catalog.CatalogTests.test_write_markdown_docs_generates_service_detail_pages -v`
Expected: FAIL because `docs/services/OpenAI.md` is not generated

- [ ] **Step 3: Write minimal implementation**

```python
def _load_upstream_docs_manifest(root: Path) -> dict[str, list[dict[str, object]]]:
    path = root / "dist" / "manifests" / "upstream_docs.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _service_detail_markdown(root: Path, catalog: Catalog, service_name: str, entries: list[dict[str, object]]) -> str:
    service = catalog.services[service_name]
    lines = [f"# {service_name}", "", service.notes or "-", ""]
    lines.extend(["## Upstream Rule Files", ""])
    for entry in entries:
        lines.append(f"- [{entry['source']}]({entry['rule_url']})")
    lines.extend(["", "## Upstream READMEs", ""])
    for entry in entries:
        lines.append(f"- [{entry['source']}]({entry['readme_url']}) - `{entry['status']}`")
    for entry in entries:
        lines.extend(["", f"## Upstream Original Text: {entry['source']}", ""])
        if entry["status"] != "ok" or not entry["snapshot_path"]:
            lines.append("upstream README missing" if entry["status"] == "missing" else "upstream README fetch_error")
            continue
        snapshot = root / str(entry["snapshot_path"])
        lines.append(snapshot.read_text(encoding="utf-8"))
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_normalize.test_catalog -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_normalize/test_catalog.py src/egloon_rule_hub/docs/render.py
git commit -m "feat: render service pages with upstream readmes"
```

### Task 4: Wire upstream README tracking into CLI bootstrap

**Files:**
- Modify: `src/egloon_rule_hub/cli.py`
- Create: `tests/test_cli/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
import json
import tempfile
import unittest
from pathlib import Path
from egloon_rule_hub.model.catalog import Catalog, ServiceDef, SourceDef, TargetDef
from unittest.mock import patch

from egloon_rule_hub.cli import main


class CliBootstrapTests(unittest.TestCase):
    def test_bootstrap_invokes_upstream_docs_builder(self) -> None:
        with patch("egloon_rule_hub.cli._run_validate") as run_validate, patch(
            "egloon_rule_hub.cli.build_all_service_rules"
        ) as build_all_service_rules, patch(
            "egloon_rule_hub.cli.render_rule_artifacts"
        ) as render_rule_artifacts, patch(
            "egloon_rule_hub.cli._render_manifests"
        ) as render_manifests, patch(
            "egloon_rule_hub.cli.write_markdown_docs"
        ) as write_markdown_docs, patch(
            "egloon_rule_hub.cli.build_upstream_docs"
        ) as build_upstream_docs:
            run_validate.return_value = object()
            build_all_service_rules.return_value = {}
            exit_code = main(["--root", ".", "bootstrap"])

        self.assertEqual(exit_code, 0)
        build_upstream_docs.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_cli.test_cli -v`
Expected: FAIL because `egloon_rule_hub.cli` does not import or call `build_upstream_docs`

- [ ] **Step 3: Write minimal implementation**

```python
from egloon_rule_hub.upstream_docs.build import build_upstream_docs


if args.command == "bootstrap":
    catalog = _run_validate(root)
    service_rules = build_all_service_rules(catalog)
    render_rule_artifacts(root, catalog, service_rules)
    _render_manifests(root, catalog)
    build_upstream_docs(catalog, fetcher=fetch_text)
    write_markdown_docs(root, catalog)
    print("Bootstrap complete")
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_cli.test_cli -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_cli/__init__.py tests/test_cli/test_cli.py src/egloon_rule_hub/cli.py
git commit -m "feat: wire upstream README tracking into bootstrap"
```

### Task 5: Refresh generated docs, update README, and verify the full flow

**Files:**
- Modify: `README.md`
- Modify: `docs/services.md`
- Create: `docs/services/*.md`
- Create: `dist/upstream-readmes/**/*`
- Modify: `dist/manifests/upstream_docs.json`

- [ ] **Step 1: Write the failing documentation assertion**

```python
def test_readme_mentions_upstream_readme_tracking(self) -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")
    self.assertIn("upstream README tracking", readme)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_normalize.test_catalog.CatalogTests.test_readme_mentions_upstream_readme_tracking -v`
Expected: FAIL because `README.md` does not mention the feature yet

- [ ] **Step 3: Write minimal implementation**

```markdown
## Documentation Tracking

- `bootstrap` now snapshots upstream `README.md` files for referenced rule sets
- generated service pages under `docs/services/` include exact rule links, README links, local summaries, and upstream original text
- `dist/manifests/upstream_docs.json` tracks README fetch status for each source entry
```

- [ ] **Step 4: Run end-to-end verification**

Run: `python -m unittest discover -s tests -p 'test_*.py' -t . -v`
Expected: PASS

Run: `python -m egloon_rule_hub bootstrap`
Expected: `Bootstrap complete`

Run: `git status --short`
Expected: generated changes only under `README.md`, `docs/`, and `dist/`

- [ ] **Step 5: Commit**

```bash
git add README.md docs dist
git commit -m "feat: publish upstream README tracking docs"
```
