 <!-- SPDX-License-Identifier: Apache-2.0
      https://www.apache.org/licenses/LICENSE-2.0 -->

# AGENTS instructions

**This is the quick reference for agents and contributors.** For detailed standards, see [CONSTITUTION.md](CONSTITUTION.md).

## Decision Rules (Agent-Prioritized)

1. **Always use Breeze** — Never run `pytest`, `python`, or `airflow` directly on the host
2. **Use `uv` for fast path** — `uv run --project <PROJECT> <command>` (host-native Python)
3. **Fallback to Breeze** — If `uv` fails with missing system dependencies: `breeze run <command>`
4. **Container fallback** — For Kubernetes/Helm tests: `breeze testing helm-tests`
5. **Environment confirmation** — Store scripts in `dev/` (mounts as `/opt/airflow/dev/` in Breeze)

## Essential Commands (By Use Case)

### Testing
- Single test: `uv run --project <PROJECT> pytest path/to/test.py::TestClass::test_method -xvs`
- Test file: `uv run --project <PROJECT> pytest path/to/test.py -xvs`
- All in package: `uv run --project <PROJECT> pytest path/to/package -xvs`
- Parallel tests: `breeze testing <test_group> --run-in-parallel`

### Development
- Run script: `uv run --project <PROJECT> python dev/my_script.py`
- Type check: `breeze run mypy path/to/code`
- Pre-commit checks: `prek run --from-ref <target_branch> --stage pre-commit`

### CI/CD Decision Tree
```
pytest fails with missing deps?
├─ Yes → breeze run pytest <tests> -xvs
└─ No → uv tests passed

Kubernetes/Helm tests?
├─ Yes → breeze testing helm-tests --use-xdist
└─ No → use uv path

Need to determine tests from diff?
├─ Yes → breeze selective-checks --commit-ref <commit>
└─ No → run targeted tests
```

## Architecture Boundaries (from CONSTITUTION.md)

1. Users author Dags with Task SDK (`airflow.sdk`)
2. Dag Processor → stores serialized Dags in metadata DB
3. Scheduler reads serialized Dags (never runs user code) → creates Dag runs
4. Workers execute tasks via Task SDK → communicate with API Server (never access metadata DB)
5. API Server serves UI and handles client-database interactions
6. Triggerer evaluates deferred tasks in isolated processes
7. Shared libraries in `shared/` are symbolically linked to distributions

## References to Standards

- **Coding Standards** → [CONSTITUTION.md § Coding Standards](CONSTITUTION.md#coding-standards)
- **Testing Standards** → [CONSTITUTION.md § Testing Standards](CONSTITUTION.md#testing-standards)
- **Commits & PRs** → [CONSTITUTION.md § Commits and PRs](CONSTITUTION.md#commits-and-prs)
- **Repository Structure** → [CONSTITUTION.md § Repository Structure](CONSTITUTION.md#repository-structure)
- **Boundaries & Guardrails** → [CONSTITUTION.md § Boundaries](CONSTITUTION.md#boundaries)
