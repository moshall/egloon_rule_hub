# egloon_rule_hub Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize `egloon_rule_hub` as a Git-backed Python project with catalog files, baseline parser and emitter modules, docs generation, and GitHub Actions workflows.

**Architecture:** The repository uses a catalog-driven architecture. Catalog files define sources, services, bundles, and targets. Python code loads and validates that catalog, renders summary manifests and docs, and establishes parser and emitter boundaries that later sync work can plug into.

**Tech Stack:** Python 3.12, PyYAML, setuptools, GitHub Actions

---

### Task 1: Create project metadata and top-level docs

**Files:**
- Create: `README.md`
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `docs/superpowers/specs/2026-04-10-egloon-rule-hub-design.md`
- Create: `docs/superpowers/plans/2026-04-10-egloon-rule-hub-initialization.md`

- [ ] Write the initial repository metadata and design docs.
- [ ] Keep the README honest about what is implemented now versus later.
- [ ] Include official rule references used to shape the initial emitter and parser boundaries.

### Task 2: Define the catalog contract

**Files:**
- Create: `catalog/sources.yaml`
- Create: `catalog/targets.yaml`
- Create: `catalog/services.yaml`
- Create: `catalog/bundles.yaml`
- Create: `overrides/services/OpenAI.yaml`

- [ ] Define the top-level source, target, service, bundle, and override schema with real sample data.
- [ ] Seed the services catalog with the requested service names.
- [ ] Keep service entries light so later source wiring can happen incrementally.

### Task 3: Build the Python package skeleton

**Files:**
- Create: `src/egloon_rule_hub/__init__.py`
- Create: `src/egloon_rule_hub/__main__.py`
- Create: `src/egloon_rule_hub/cli.py`
- Create: `src/egloon_rule_hub/model/rules.py`
- Create: `src/egloon_rule_hub/model/catalog.py`
- Create: `src/egloon_rule_hub/sources/*.py`
- Create: `src/egloon_rule_hub/parsers/*.py`
- Create: `src/egloon_rule_hub/normalize/*.py`
- Create: `src/egloon_rule_hub/emitters/*.py`
- Create: `src/egloon_rule_hub/docs/render.py`

- [ ] Implement catalog loading and validation first.
- [ ] Add a small CLI with `validate-catalog`, `render-manifests`, `render-docs`, and `bootstrap`.
- [ ] Keep parser and emitter code small but runnable.

### Task 4: Add tests and workflows

**Files:**
- Create: `tests/test_parsers/test_parsers.py`
- Create: `tests/test_emitters/test_emitters.py`
- Create: `tests/test_normalize/test_catalog.py`
- Create: `.github/workflows/validate.yml`
- Create: `.github/workflows/sync-rules.yml`

- [ ] Add basic unit tests for catalog loading, parser behavior, and emitter output.
- [ ] Make validation and bootstrap executable in GitHub Actions.
- [ ] Keep the sync workflow conservative for now, only validating and refreshing generated docs and manifests.

### Task 5: Verify locally

**Files:**
- Modify: generated docs and manifests after running the CLI

- [ ] Initialize the repo with `git init -b main`.
- [ ] Install the package in a local virtual environment.
- [ ] Run unit tests.
- [ ] Run `python -m egloon_rule_hub bootstrap`.
- [ ] Confirm generated docs and manifests exist and reflect the catalog.

