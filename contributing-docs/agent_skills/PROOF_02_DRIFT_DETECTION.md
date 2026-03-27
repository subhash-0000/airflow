# Proof 2: Drift Detection Working

**Purpose:** Demonstrates that skills.json stays in sync with contributing-docs/*.rst source files.

---

## Command 1: Generate Fresh skills.json

```bash
cd scripts/ci/prek
python3 extract_agent_skills.py
```

### Output

```
Written 4 skill(s) to .github/skills/breeze-contribution/skills.json
  - static-checks
  - run-tests
  - system-verify
  - create-pr-description
```

---

## Command 2: Check for Drift

```bash
python3 extract_agent_skills.py --check
```

### Output (In Sync - PASS)

```
OK: skills.json is in sync with contributing-docs/*.rst
```

---

## Command 3: Simulate Drift (Test Failure Path)

```bash
# Manually edit skills.json to introduce drift
python3 extract_agent_skills.py --check
```

### Output (Drift Detected - FAIL)

```
DRIFT: skills.json is out of sync with contributing-docs/*.rst

Expected changes:
  - run-tests: local command updated
  - system-verify: fallback_condition changed

Run without --check to regenerate.
```

**Exit code:** `1` (fails CI when drift detected)

---

## How It Works

```
┌─────────────────────────────────────────────┐
│  contributing-docs/*.rst (Source of Truth)  │
│  .. agent-skill:: directives embedded       │
└─────────────────────────────────────────────┘
                    ↓
         extract_agent_skills.py
         (RST directive parser)
                    ↓
         .github/skills/breeze-contribution/
         skills.json (Auto-generated)
                    ↓
         prek hook (wired in .pre-commit-config.yaml)
                    ↓
         --check mode exits 1 on drift
```

---

## Prek Hook Integration

**Location:** `.pre-commit-config.yaml` (lines 942-951)

```yaml
- repo: local
  hooks:
    - id: check-breeze-contribution-skills-drift
      name: Check Breeze Contribution Skills Drift
      entry: python3 scripts/ci/prek/extract_agent_skills.py --check
      language: system
      pass_filenames: false
      always_run: true
      stages: [pre-commit]
```

---

## Why This Matters

1. **Prevents drift** — skills.json cannot diverge from source docs
2. **CI enforcement** — PRs fail if skills not regenerated
3. **Single source of truth** — contributing-docs/*.rst is canonical
4. **Automatic sync** — developers run extraction before commit

---

## Files Involved

| File | Purpose |
|------|---------|
| `scripts/ci/prek/extract_agent_skills.py` | RST parser + drift detection |
| `.github/skills/breeze-contribution/skills.json` | Auto-generated skill definitions |
| `contributing-docs/03_contributors_quick_start.rst` | Source: run-tests, system-verify skills |
| `contributing-docs/08_static_code_checks.rst` | Source: static-checks skill |
| `.pre-commit-config.yaml` | Prek hook wiring |

---

**Branch:** `feat/executable-doc-agent-skills`
