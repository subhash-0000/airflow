# Visual Proof — Agent Skills PoC Execution Evidence

**Branch:** `feat/executable-doc-agent-skills`

This directory contains execution evidence demonstrating that the agent skills system works end-to-end.

---

## Quick Summary

| Proof | What It Shows | Status |
|-------|---------------|--------|
| [Proof 1](#proof-1-test-suite-passing) | 51 tests passing | ✅ |
| [Proof 2](#proof-2-drift-detection-working) | Drift detection working | ✅ |
| [Proof 3](#proof-3-context-detection-api-working) | Context API working | ✅ |
| [Proof 4](#proof-4-intelligent-3-tier-fallback-working) | 3-tier fallback working | ✅ |

---

## Proof 1: Test Suite Passing

**51 tests passing in 0.45s**

✅ **Full details:** [PROOF_01_TESTS_PASSING.md](./PROOF_01_TESTS_PASSING.md)

**Categories covered:**
- RST Parsing (5 tests)
- Skill Extraction (7 tests)
- Drift Detection (4 tests)
- Context Detection (8 tests)
- Intelligent Fallback (19 tests)
- Integration (2 tests)

---

## Proof 2: Drift Detection Working

**skills.json stays in sync with contributing-docs/*.rst**

✅ **Full details:** [PROOF_02_DRIFT_DETECTION.md](./PROOF_02_DRIFT_DETECTION.md)

**What it proves:**
- Extraction from RST directives works
- `--check` mode detects drift
- Prek hook enforces sync in CI

---

## Proof 3: Context Detection API Working

**Automatic host vs Breeze detection**

✅ **Full details:** [PROOF_03_CONTEXT_DETECTION.md](./PROOF_03_CONTEXT_DETECTION.md)

**What it proves:**
- Priority chain: env var → dockerenv → mount point → default
- Correct command selection per context
- Runtime API for agents to call

---

## Proof 4: Intelligent 3-Tier Fallback Working

**NATIVE → BREEZE → SYSTEM with error-driven selection**

✅ **Full details:** [PROOF_04_INTELLIGENT_FALLBACK.md](./PROOF_04_INTELLIGENT_FALLBACK.md)

**What it proves:**
- 70% time savings (NATIVE vs BREEZE)
- IDE-debuggable workflows (uv run)
- Error-driven command selection

---

## How to Reproduce

### Run All Proofs

```bash
cd airflow/contributing-docs/agent_skills

# Proof 1: Tests
cd ../../scripts/ci/prek
python3 -m pytest test_breeze_agent_skills.py -v

# Proof 2: Drift detection
python3 extract_agent_skills.py
python3 extract_agent_skills.py --check

# Proof 3: Context detection
python3 -c "from breeze_context_detect import detect_environment; print(detect_environment())"
AIRFLOW_BREEZE_CONTAINER=1 python3 -c "from breeze_context_detect import detect_environment; print(detect_environment())"

# Proof 4: Intelligent fallback
python3 -c "from intelligent_fallback import get_command; print(get_command('run-tests', test_path='tests/foo.py'))"
```

---

## Key Files

| File | Purpose |
|------|---------|
| `scripts/ci/prek/test_breeze_agent_skills.py` | 51 tests |
| `scripts/ci/prek/extract_agent_skills.py` | RST parser + drift detection |
| `scripts/ci/prek/breeze_context_detect.py` | Context API |
| `scripts/ci/prek/intelligent_fallback.py` | 3-tier fallback |
| `.github/skills/breeze-contribution/skills.json` | Auto-generated skills |
| `contributing-docs/*.rst` | Source of truth (embedded skills) |

---

## What This Proves

1. ✅ **Comprehensive testing** — 51 tests validate all components
2. ✅ **No drift possible** — Executable document pattern enforces sync
3. ✅ **Context-aware** — Automatic host/Breeze detection
4. ✅ **Fast feedback** — NATIVE tier 70% faster than BREEZE
5. ✅ **Production-ready** — Prek hook wired, CI enforcement

---

**Branch:** `feat/executable-doc-agent-skills`
