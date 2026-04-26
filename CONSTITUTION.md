 <!-- SPDX-License-Identifier: Apache-2.0
      https://www.apache.org/licenses/LICENSE-2.0 -->

# Apache Airflow Constitution

**The detailed rules and standards for contributing to Apache Airflow.** Quick reference: [AGENTS.md](AGENTS.md)

---

## Repository Structure

UV workspace monorepo. Key paths:

- `airflow-core/src/airflow/` — core scheduler, API, CLI, models
  - `models/` — SQLAlchemy models (DagModel, TaskInstance, DagRun, Asset, etc.)
  - `jobs/` — scheduler, triggerer, Dag processor runners
  - `api_fastapi/core_api/` — public REST API v2, UI endpoints
  - `api_fastapi/execution_api/` — task execution communication API
  - `dag_processing/` — Dag parsing and validation
  - `cli/` — command-line interface
  - `ui/` — React/TypeScript web interface (Vite)
- `task-sdk/` — lightweight SDK for Dag authoring and task execution runtime
  - `src/airflow/sdk/execution_time/` — task runner, supervisor
- `providers/` — 100+ provider packages, each with its own `pyproject.toml`
- `airflow-ctl/` — management CLI tool
- `chart/` — Helm chart for Kubernetes deployment
- `dev/` — development utilities and scripts used to bootstrap the environment, releases, breeze dev env
- `scripts/` — utility scripts for CI, Docker, and prek hooks (workspace distribution `apache-airflow-scripts`)
  - `ci/prek/` — prek (pre-commit) hook scripts; shared utilities in `common_prek_utils.py`
  - `tests/` — pytest tests for the scripts; run with `uv run --project scripts pytest scripts/tests/`

### Shared Libraries

- Shared libraries provide implementation of common utilities (logging, configuration) for reuse across distributions
- Located in `shared/` folder as separate, small Python distributions
- Each library has its own src, tests, `pyproject.toml`, and dependencies
- Sources are symbolically linked to distributions that need them (`airflow-core`, `task-sdk`, etc.)
- Internal tests run from shared distribution; tests of consumers run from consuming distributions

---

## Architecture Boundaries

**These boundaries define how the system components interact:**

1. **Dag Authoring** — Users author Dags with the Task SDK (`airflow.sdk`)
2. **Dag Processing** — Dag Processor parses Dag files in isolated processes and stores serialized Dags in metadata DB
3. **Scheduling** — Scheduler reads serialized Dags (never runs user code) and creates Dag runs / task instances
4. **Task Execution** — Workers execute tasks via Task SDK and communicate with API Server through Execution API (never access metadata DB directly)
5. **API & UI** — API Server serves React UI and handles all client-database interactions
6. **Deferred Tasks** — Triggerer evaluates deferred tasks/sensors in isolated processes
7. **Workspace** — Airflow uses `uv workspace` feature to keep all distributions sharing dependencies and venv
8. **Project Syncing** — Each distribution declares dependencies; `uv --project <FOLDER> sync` acts on selected project with only its dependencies

---

## Coding Standards

### Import Organization
- Imports at top of file
- Valid exceptions:
  - Circular imports
  - Lazy loading for worker isolation
  - `TYPE_CHECKING` blocks for type-only imports

### Import Guards for Multi-Process Code
- Guard heavy type-only imports (e.g., `kubernetes.client`) with `TYPE_CHECKING` in multi-process code paths
- Prevents import errors in worker processes

### Exception Handling
- Define dedicated exception classes or use existing exceptions like `ValueError`
- Never raise broad `AirflowException` directly
- Each error case should have a specific exception type that conveys what went wrong

### Code Quality
- **Always format and check Python files with ruff immediately after writing or editing them:**
  - `uv run ruff format <file_path>`
  - `uv run ruff check --fix <file_path>`
  - Do this for every Python file you create or modify before moving on
- No `assert` in production code
- `time.monotonic()` for durations, not `time.time()`

### Session Handling (airflow-core specific)
- Functions with a `session` parameter must not call `session.commit()`
- Use keyword-only `session` parameters

### File Headers
- Apache License header on all new files (prek enforces this)

---

## Testing Standards

### Test Organization
- Add tests for new behavior—cover success, failure, and edge cases
- Test location mirrors source: `airflow/cli/cli_parser.py` → `tests/cli/test_cli_parser.py`

### Test Patterns
- Use pytest patterns, not `unittest.TestCase`
- Use `spec`/`autospec` when mocking
- Use `time_machine` for time-dependent tests
- Use `@pytest.mark.parametrize` for multiple similar inputs
- Use `@pytest.mark.db_test` for tests requiring database access

### Test Fixtures
- Located at `devel-common/src/tests_common/pytest_plugin.py`
- Use these fixtures for consistency across test suite

---

## Commits and PRs

### Commit Messages
Write commit messages focused on user impact, not implementation details.

**Good examples:**
- `Fix airflow dags test command failure without serialized Dags`
- `UI: Fix Grid view not refreshing after task actions`

**Bad examples:**
- `Initialize DAG bundles in CLI get_dag function`

### Newsfragments
Add a newsfragment for user-visible changes:

```bash
echo "Brief description" > airflow-core/newsfragments/{PR_NUMBER}.{bugfix|feature|improvement|doc|misc|significant}.rst
```

### Co-Authorship
- NEVER add Co-Authored-By with yourself as co-author of the commit
- Agents are assistants, not authors—humans are the authors

### Creating Pull Requests

**Always push to the user's fork**, not to upstream `apache/airflow`. Never push directly to `main`.

#### Determine Fork Remote

Check `git remote -v`:
- If `origin` does NOT point to `apache/airflow`, use `origin` (it's your fork)
- If `origin` points to `apache/airflow`, find another remote pointing to your fork
- If no fork remote exists, create one:
  ```bash
  gh repo fork apache/airflow --remote --remote-name fork
  ```

#### Pre-Push Checklist

Perform self-review following Gen-AI review guidelines in [`contributing-docs/05_pull_requests.rst`](contributing-docs/05_pull_requests.rst) and code review checklist in [`.github/instructions/code-review.instructions.md`](.github/instructions/code-review.instructions.md):

1. Review full diff: `git diff main...HEAD`
   - Verify every change is intentional and related to the task
   - Remove any unrelated changes
2. Check against all rules in `.github/instructions/code-review.instructions.md`:
   - Architecture boundaries
   - Database correctness
   - Code quality
   - Testing requirements
   - API correctness
   - AI-generated code signals
3. Confirm code follows coding standards and architecture boundaries
4. Run fast static checks: `prek run --from-ref <target_branch> --stage pre-commit`
5. Run slow static checks: `prek run --from-ref <target_branch> --stage manual`
6. Run relevant individual tests
7. Determine tests from diff: `breeze selective-checks --commit-ref <commit>`
8. Check for security issues—no secrets, no injection vulnerabilities, no unsafe patterns

#### Rebase Before Pushing

Always rebase onto latest target branch to avoid merge conflicts and ensure CI runs against up-to-date code:

```bash
git fetch <upstream-remote> <target_branch>
git rebase <upstream-remote>/<target_branch>
```

If conflicts occur, resolve them and continue rebase. If too complex, ask for guidance.

#### Push and Create PR

Push branch and open PR creation page with pre-filled body (including Gen-AI disclosure):

```bash
git push -u <fork-remote> <branch-name>
gh pr create --web --title "Short title (under 70 chars)" --body "$(cat <<'EOF'
Brief description of the changes.

closes: #ISSUE  (if applicable)

---

##### Was generative AI tooling used to co-author this PR?

- [X] Yes — <Agent Name and Version>

Generated-by: <Agent Name and Version> following [the guidelines](https://github.com/apache/airflow/blob/main/contributing-docs/05_pull_requests.rst#gen-ai-assisted-contributions)

EOF
)"
```

The `--web` flag opens browser for review. The `--body` flag pre-fills PR template with Gen-AI disclosure completed.

#### PR Submission Reminders

After creation, remember to:

1. Review PR title—keep it short (under 70 chars) and focused on user impact
2. Add brief description of changes at top of body
3. Reference related issues when applicable (`closes: #ISSUE` or `related: #ISSUE`)

---

## Boundaries & Guardrails

### Ask First
- Large cross-package refactors
- New dependencies with broad impact
- Destructive data or migration changes

### Never
- Commit secrets, credentials, or tokens
- Edit generated files by hand when a generation workflow exists
- Use destructive git operations unless explicitly requested

---

## Environment Setup (From AGENTS.md)

- Install prek: `uv tool install prek`
- Enable commit hooks: `prek install`
- Never run `pytest`, `python`, or `airflow` commands directly on host—always use Breeze
- Place temporary scripts in `dev/` (mounts as `/opt/airflow/dev/` in Breeze)

---

## Additional Resources

- [`contributing-docs/03a_contributors_quick_start_beginners.rst`](contributing-docs/03a_contributors_quick_start_beginners.rst)
- [`contributing-docs/05_pull_requests.rst`](contributing-docs/05_pull_requests.rst)
- [`contributing-docs/07_local_virtualenv.rst`](contributing-docs/07_local_virtualenv.rst)
- [`contributing-docs/08_static_code_checks.rst`](contributing-docs/08_static_code_checks.rst)
- [`contributing-docs/12_provider_distributions.rst`](contributing-docs/12_provider_distributions.rst)
- [`contributing-docs/19_execution_api_versioning.rst`](contributing-docs/19_execution_api_versioning.rst)
