# Proof 3: Context Detection API Working

**Purpose:** Demonstrates runtime detection of host vs Breeze container environments.

---

## Command 1: Detect Host Environment (Default)

```bash
cd scripts/ci/prek
python3 -c "from breeze_context_detect import detect_environment; print(detect_environment())"
```

### Output

```
EnvironmentEvidence(environment='host', reason='default')
```

---

## Command 2: Detect Breeze Environment (Forced via Env Var)

```bash
AIRFLOW_BREEZE_CONTAINER=1 python3 -c "from breeze_context_detect import detect_environment; print(detect_environment())"
```

### Output

```
EnvironmentEvidence(environment='breeze-container', reason='AIRFLOW_BREEZE_CONTAINER')
```

---

## Command 3: Detect Breeze Environment (Docker Marker)

```bash
python3 -c "
from breeze_context_detect import detect_environment
from unittest.mock import patch
from pathlib import Path

with patch.object(Path, 'exists', return_value=True):
    print(detect_environment())
"
```

### Output

```
EnvironmentEvidence(environment='breeze-container', reason='/.dockerenv')
```

---

## Command 4: Get Command for Current Context

```bash
python3 -c "
from breeze_context_detect import plan_command, detect_environment

skill = {
    'id': 'run-tests',
    'local': 'uv run --project {dist} pytest {path} -xvs',
    'fallback': 'pytest {path} -xvs',
    'fallback_condition': 'missing_system_deps'
}

env = detect_environment()
cmd = plan_command(skill, {'dist': 'airflow-core', 'path': 'tests/foo.py'})

print(f'Environment: {env.environment}')
print(f'Command: {cmd}')
"
```

### Output

```
Environment: host
Command: uv run --project airflow-core pytest tests/foo.py -xvs
```

---

## Command 5: Get Command for Breeze Context

```bash
AIRFLOW_BREEZE_CONTAINER=1 python3 -c "
from breeze_context_detect import plan_command, detect_environment

skill = {
    'id': 'run-tests',
    'local': 'uv run --project {dist} pytest {path} -xvs',
    'fallback': 'pytest {path} -xvs',
    'fallback_condition': 'missing_system_deps'
}

env = detect_environment()
cmd = plan_command(skill, {'dist': 'airflow-core', 'path': 'tests/foo.py'})

print(f'Environment: {env.environment}')
print(f'Command: {cmd}')
"
```

### Output

```
Environment: breeze-container
Command: pytest tests/foo.py -xvs
```

---

## Context Detection Priority Chain

```
Priority 1: AIRFLOW_BREEZE_CONTAINER=1 (explicit override)
              ↓
Priority 2: /.dockerenv exists (Docker container marker)
              ↓
Priority 3: /opt/airflow exists (Breeze mount point)
              ↓
Default:    host (local development)
```

---

## API Reference

### `detect_environment()`

Returns: `EnvironmentEvidence` dataclass

```python
@dataclass(frozen=True)
class EnvironmentEvidence:
    environment: str  # 'host' or 'breeze-container'
    reason: str       # Why this environment was detected
```

### `plan_command(skill, params)`

Returns: `str` (command to execute)

```python
def plan_command(skill: dict, params: dict) -> str:
    """
    Select appropriate command based on:
    - Current environment (host vs breeze)
    - Skill definition (local, fallback, tier)
    - Failure reason (if any)
    """
```

---

## Why This Matters

1. **Automatic context detection** — Agents don't need manual configuration
2. **Correct command selection** — Host gets `uv run`, Breeze gets plain `pytest`
3. **Priority chain** — Explicit override > Docker markers > Default
4. **Runtime API** — Simple function calls for agents to use

---

## Files Involved

| File | Purpose |
|------|---------|
| `scripts/ci/prek/breeze_context_detect.py` | Context detection API |
| `.github/skills/breeze-contribution/skills.json` | Skill definitions |

---

**Branch:** `feat/executable-doc-agent-skills`
