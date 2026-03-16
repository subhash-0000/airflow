# Airflow Breeze Contribution Skills

**Version:** 1.0.0 (March 2026)
**Source of truth:** `contributing-docs/*.rst` (executable document pattern)

---

## Executive Summary

This directory contains **auto-generated** agent skills for AI assistants (Claude Code, GitHub Copilot, etc.) contributing to Apache Airflow.

**Key principle:** Skills are extracted from `contributing-docs/*.rst` — the same documentation humans read. This ensures:

1. ✅ **No drift possible** — Skills and docs are the same file
2. ✅ **Human + Agent readable** — `.. agent-skill::` directives are embedded in prose
3. ✅ **Automated sync** — Prek hook fails CI if `skills.json` diverges from source

---

## Files in This Directory

| File | Purpose | Editable? |
|------|---------|-----------|
| `SKILL.md` | This file — documentation about the skills system | ✅ Yes |
| `skills.json` | Auto-generated skill definitions | ❌ No (run `extract_agent_skills.py`) |

---

## How It Works

### 1. Skills Are Embedded in Contributing Docs

Developers add `.. agent-skill::` directives directly in `contributing-docs/*.rst`:

```rst
Running Tests
-------------

.. agent-skill:: run-tests
   :host: uv run --project {dist} pytest {path} -xvs
   :breeze: pytest {path} -xvs
   :fallback_condition: missing_system_deps

To run tests locally, use the following command:
```

### 2. Extraction Pipeline

The script `scripts/ci/prek/extract_agent_skills.py`:
1. Scans all `contributing-docs/*.rst` files
2. Parses `.. agent-skill::` directives
3. Generates `skills.json`

```bash
# Generate skills.json
python3 scripts/ci/prek/extract_agent_skills.py

# Check for drift (CI mode)
python3 scripts/ci/prek/extract_agent_skills.py --check
```

### 3. Prek Hook Enforces Sync

The prek hook (wired in `.pre-commit-config.yaml`) runs `--check` mode:
- If `skills.json` matches `contributing-docs/*.rst` → ✅ Pass
- If `skills.json` diverges → ❌ Fail CI, run extraction script

---

## Available Skills

| Workflow | Host Command | Breeze Command | Fallback Condition | Source File |
|----------|--------------|----------------|-------------------|-------------|
| `static-checks` | `prek run --from-ref main --stage pre-commit` | `prek run --from-ref main --stage pre-commit` | never | `08_static_code_checks.rst` |
| `run-tests` | `uv run --project {dist} pytest {path} -xvs` | `pytest {path} -xvs` | `missing_system_deps` | `03_contributors_quick_start.rst` |
| `system-verify` | `breeze start-airflow` | `airflow info` | never | `03_contributors_quick_start.rst` |

---

## For AI Agents

### How to Use Skills

1. **Load `skills.json`** at runtime
2. **Detect your context** using `breeze_context_detect.py`:
   ```python
   from breeze_context_detect import is_inside_breeze, get_command

   if is_inside_breeze():
       context = "breeze"
   else:
       context = "host"

   cmd = get_command("run-tests", test_path="tests/unit/test_foo.py")
   # Returns: {"context": "host", "command": "uv run --project ...", ...}
   ```
3. **Execute the command** for your context

### Context Detection Priority

The runtime detects context using this priority chain:

1. `AIRFLOW_BREEZE_CONTAINER=1` env var (explicit override)
2. `/.dockerenv` file exists (Docker container marker)
3. `/opt/airflow` directory exists (Breeze mount point)

---

## For Human Contributors

### Adding a New Skill

1. Open the relevant `contributing-docs/*.rst` file
2. Add a `.. agent-skill::` directive where the command is documented:
   ```rst
   .. agent-skill:: my-workflow
      :host: command-for-host
      :breeze: command-for-breeze
      :fallback_condition: when-to-fallback
   ```
3. Run the extraction script:
   ```bash
   python3 scripts/ci/prek/extract_agent_skills.py
   ```
4. Commit both the `.rst` change and the updated `skills.json`

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| `workflow` | Unique workflow name (from directive) | `run-tests` |
| `host` | Command to run on host machine | `uv run --project airflow-core pytest ...` |
| `breeze` | Command to run inside Breeze container | `pytest ...` |
| `fallback_condition` | When to fall back to Breeze | `missing_system_deps`, `never` |

---

## Architecture Decisions

### Why Contributing Docs as Source of Truth?

**Problem:** Previous approaches used separate files (e.g., `SKILL.md`, `AGENTS.md`) for skills. These could drift from human documentation.

**Solution:** Embed skills directly in `contributing-docs/*.rst`. Benefits:
- **Single source of truth** — Same file serves humans and agents
- **No drift** — Impossible for docs and skills to diverge
- **Maintainability** — Update once, both benefit

### Why RST Directives?

**Alternatives considered:**
- Markdown comments (`<!-- agent-skill-sync: -->`) — Only works for Markdown files
- YAML frontmatter — Not native to RST
- Separate JSON/YAML files — Drift risk

**Decision:** RST directives are:
- Native to the documentation format
- Parseable by docutils (Apache's RST parser)
- Invisible to rendered HTML (don't affect human readers)

### Why Prek Hook?

**Goal:** Ensure skills.json never drifts from source.

**Implementation:** Prek hook runs `extract_agent_skills.py --check`:
- Fast (parses only changed files)
- Fails CI on drift (enforces maintenance)
- Same pattern as `update-breeze-cmd-output` (line 909 of `.pre-commit-config.yaml`)

---

## Testing

Run tests with:
```bash
python3 -m pytest scripts/ci/prek/test_breeze_agent_skills.py -v
```

Tests cover:
- RST directive parsing
- Skill extraction from multiple files
- JSON generation
- Drift detection
- Context detection (host vs. Breeze)

---

## Related Files

| Path | Purpose |
|------|---------|
| `scripts/ci/prek/extract_agent_skills.py` | Extraction pipeline |
| `scripts/ci/prek/breeze_context_detect.py` | Runtime context detection API |
| `scripts/ci/prek/test_breeze_agent_skills.py` | Pytest tests |
| `.pre-commit-config.yaml` | Prek hook configuration (line 942-951) |
| `contributing-docs/*.rst` | Source of truth (human + agent docs) |

---

## Changelog

### v1.0.0 (March 2026)
- **Breaking:** Moved source of truth from `SKILL.md` to `contributing-docs/*.rst`
- **New:** RST directive parser (`.. agent-skill::`)
- **New:** Source file tracking in `skills.json`
- **Improved:** Drift detection now compares against actual docs

### v0.1.0 (March 2026)
- Initial PoC with markdown comment markers in `SKILL.md`
- 3 skills: `static-checks`, `run-tests`, `system-verify`
- Prek hook integration

---

**Maintained by:** GSoC 2026 Contribution & Verification Agent Skills Project
**Last updated:** March 16, 2026
