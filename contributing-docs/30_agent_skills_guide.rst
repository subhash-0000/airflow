..
    Licensed to the Apache Software Foundation (ASF) under one
    or more contributor license agreements.  See the NOTICE file
    distributed with this work for additional information
    regarding copyright ownership.  The ASF licenses this file
    to you under the Apache License, Version 2.0 (the
    "License"); you may not use this file except in compliance
    with the License.  You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing,
    software distributed under the License is distributed on an
    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
    KIND, either express or implied.  See the License for the
    specific language governing permissions and limitations
    under the License.

.. _contributing_agentskills:

==========================
Contributing Agent Skills
==========================

This guide explains how to add new agent skills to Apache Airflow. Agent skills are commands and
workflows that agents (like GitHub Copilot) use to interact with the Airflow development environment.

**Quick Links:**
- :doc:`AGENTS` — Quick reference for running commands in the development environment
- :doc:`CONSTITUTION` — Detailed standards and architecture rules
- `.github/skills/breeze-contribution/skills.json`_ — Generated skill definitions (do not edit manually)
- `.github/skills/breeze-contribution/decision_rules.json`_ — Formalized decision rules

---

Overview: Why Skills Matter
===========================

Agent skills serve two purposes:

1. **Human documentation** — Help developers understand how to run commands in Airflow development
2. **Agent context** — Enable GitHub Copilot and other agents to suggest correct commands in chat

Skills are defined in RST documentation files and automatically extracted into machine-readable JSON.
This ensures they stay synchronized with documentation — they're the same source, not separate files.

---

Adding Your First Agent Skill
=============================

Step 1: Choose or Create a Contributing Doc File
-------------------------------------------------

Skills are defined in ``contributing-docs/*.rst`` files. Choose an appropriate file or create a new one:

- ``contributing-docs/03_*.rst`` — Quick-start guides
- ``contributing-docs/05_*.rst`` — Workflow guides (PRs, testing, etc.)
- ``contributing-docs/08_*.rst`` — Static checks and linting

If your skill doesn't fit an existing file, create a new one following the pattern:
``contributing-docs/XX_descriptive_name.rst``

Step 2: Define the Skill Using RST Directive
---------------------------------------------

Add a skill definition to your chosen RST file using the ``agent-skill`` directive:

.. code-block:: rst

    Running a Single Test
    =====================

    .. agent-skill:: run-single-test
       :host: uv run --project <PROJECT> pytest path/to/test.py::TestClass::test_method -xvs
       :breeze: breeze run pytest path/to/test.py::TestClass::test_method -xvs
       :fallback_condition: If ``uv`` command fails with missing system dependencies
       :reference: AGENTS.md § Commands

    To run a specific test in isolation (useful for debugging):

    1. Identify the test file and test method (e.g., ``tests/cli/test_cli_parser.py::TestParser::test_parse_args``)
    2. Run the command above with your paths substituted
    3. Add ``-xvs`` flags to stop on first failure and show verbose output

Schema Reference
----------------

The ``agent-skill`` directive accepts the following fields:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Description
   * - ``workflow`` (required)
     - Unique identifier for this skill (e.g., ``run-single-test``)
   * - ``host`` (required)
     - Command to run on the host machine (using native ``uv`` when possible)
   * - ``breeze`` (required)
     - Fallback command to run inside the Breeze container (if host fails)
   * - ``fallback_condition`` (optional)
     - When to use the breeze command instead of host command
   * - ``reference`` (optional)
     - Link to related documentation or decision rules
   * - ``tier`` (optional)
     - Execution tier: ``native`` or ``container`` (defaults to ``native``)

**Example: Complete Skill Definition**

.. code-block:: rst

    .. agent-skill:: run-provider-tests
       :host: breeze testing providers-tests --test-type "Providers[amazon]" --run-in-parallel
       :breeze: breeze testing providers-tests --test-type "Providers[amazon]" --run-in-parallel
       :fallback_condition: Both commands run in Breeze (no host fallback)
       :tier: container
       :reference: AGENTS.md § Commands

Best Practices
==============

Command Design
--------------

✅ **DO:**
- Keep commands concise — one clear action per skill
- Use ``<VARIABLE>`` syntax for user-replaceable parts (e.g., ``<PROJECT>``, ``<TARGET_BRANCH>``)
- Include explanatory text in the RST documentation, not just the command
- Make host and breeze commands different (host uses ``uv``, breeze uses ``breeze`` CLI)

❌ **DON'T:**
- Create identical host and breeze commands (copy-paste error detector will warn)
- Use hardcoded paths or temporary file names
- Mix multiple unrelated commands in one skill
- Exceed 200 tokens (roughly 150 words) for the skill definition

Documentation
--------------

Structure your skill documentation like this:

1. **Heading** — What does this skill do?
2. **Skill directive** — The agent-skill RST block
3. **Explanation** — Why you'd use this, when to use it, what it accomplishes
4. **Examples** — Concrete usage examples for humans (optional)
5. **Troubleshooting** — Common issues and solutions (optional)

Example:

.. code-block:: rst

    Running Type Checks
    ===================

    .. agent-skill:: type-check
       :host: breeze run mypy path/to/code
       :breeze: breeze run mypy path/to/code
       :fallback_condition: Never (always runs in Breeze)
       :reference: AGENTS.md § Development

    Type checking with ``mypy`` requires a full Airflow stack and all dependencies installed.
    Always run in Breeze to ensure consistency.

    **Use this skill when:**
    - You've added or modified type-hinted code
    - You want to catch subtle type errors before submitting a PR

    **Example: Type-check the CLI module**

    .. code-block:: bash

        breeze run mypy airflow-core/src/airflow/cli

Naming Conventions
------------------

- Use kebab-case for skill IDs: ``run-single-test``, ``static-checks``, ``build-docs``
- Include the action or workflow: ``run-*``, ``build-*``, ``test-*``, ``validate-*``
- Keep IDs descriptive but short (< 40 characters)

---

Step 3: Test Your Skill Definition
-----------------------------------

Once you've added the skill to your RST file, run the extraction script to verify it's valid:

.. code-block:: bash

    python3 scripts/ci/prek/extract_agent_skills.py

This will:
- Parse all ``.. agent-skill::`` directives
- Validate schema (required fields, types, syntax)
- Detect duplicates
- Generate or update ``.github/skills/breeze-contribution/skills.json``

If validation fails, you'll see an error message like:

.. code-block:: text

    ERROR: Skill 0: Missing required field 'breeze' in skill run-single-test
    ERROR: Skill 1 (run-tests): 'host' must be a string, got dict

Fix any errors and re-run the extraction script.

Step 4: Verify with Pre-Commit Hooks
-------------------------------------

Before committing, run the pre-commit checks:

.. code-block:: bash

    prek run --from-ref main --stage pre-commit

This ensures:
- Your RST is syntactically valid
- Skills.json is in sync with your RST changes
- No formatting issues

Step 5: Commit and Push
-----------------------

Commit both the RST file and the generated ``skills.json``:

.. code-block:: bash

    git add contributing-docs/XX_your_file.rst .github/skills/breeze-contribution/skills.json
    git commit -m "Add agent skill: <id>"
    git push -u <fork-remote> <branch-name>

---

Common Patterns
===============

Pattern 1: Host vs. Breeze Fallback
-----------------------------------

Most skills have this pattern:

- **Host command** uses ``uv run ...`` for speed
- **Breeze command** is the fallback if ``uv`` fails with system dependency errors

.. code-block:: rst

    .. agent-skill:: lint-code
       :host: uv run --project <PROJECT> ruff check path/to/code
       :breeze: breeze run ruff check path/to/code
       :fallback_condition: If ``uv`` fails with "module not found" or similar

Pattern 2: Breeze-Only Commands
--------------------------------

Some commands require Breeze (Docker) because they need containers, K8s, or the full stack:

.. code-block:: rst

    .. agent-skill:: run-helm-tests
       :host: not_applicable
       :breeze: breeze testing helm-tests --use-xdist --kubernetes-version 1.35.0
       :fallback_condition: N/A — requires Kubernetes cluster and Docker daemon

Pattern 3: Variable Substitution
---------------------------------

Use ``<VARIABLE>`` placeholders for user-specific values:

.. code-block:: rst

    .. agent-skill:: run-tests-for-project
       :host: uv run --project <PROJECT> pytest <TEST_PATH> -xvs
       :breeze: breeze run pytest <TEST_PATH> -xvs

Users replace:
- ``<PROJECT>`` with the actual folder (e.g., ``airflow-core``, ``providers/amazon``)
- ``<TEST_PATH>`` with the path to tests (e.g., ``tests/cli/test_cli_parser.py``)

---

Troubleshooting
===============

"ERROR: Duplicate skill ID found"
---------------------------------

**Problem:** You defined a skill with an ID that already exists.

**Solution:**
1. Search the ``contributing-docs/`` directory for your skill ID
2. Rename your skill to something unique (or remove the duplicate)
3. Re-run the extraction script

"DRIFT DETECTED: committed skills.json does not match contributing-docs"
---------------------------------------------------------------------------

**Problem:** Your RST file changed, but you didn't regenerate ``skills.json``.

**Solution:**
.. code-block:: bash

    python3 scripts/ci/prek/extract_agent_skills.py
    git add .github/skills/breeze-contribution/skills.json
    git commit --amend

"WARNING: Skill size exceeds 150 tokens"
----------------------------------------

**Problem:** Your skill definition is too large.

**Solution:**
- Move detailed explanation into the RST documentation (outside the skill directive)
- Keep the ``host`` and ``breeze`` commands concise
- Remove redundant text; let humans read it in the doc, agents get the concise version

"Command appears incomplete (ends with pipe/backslash/operator)"
---------------------------------------------------------------

**Problem:** Your command string ends with ``|``, ``\``, ``&&``, etc.

**Solution:**
- Ensure your command is complete in the RST directive
- If it needs to continue on the next line, use proper line continuation

---

Validating Your Contribution
=============================

Before submitting a PR with a new skill, verify:

1. ✅ Skill directive is syntactically valid (required fields present)
2. ✅ Skill ID is unique (no duplicates in contributing-docs)
3. ✅ Command syntax is valid (balanced quotes, no trailing pipes)
4. ✅ Skill size is reasonable (< 200 tokens)
5. ✅ RST file is properly formatted
6. ✅ ``skills.json`` is regenerated and matches your changes
7. ✅ Pre-commit checks pass

Automated checks ensure:

.. list-table::
   :header-rows: 1

   * - Check
     - When
     - Failure Behavior
   * - Extraction validation
     - Per-commit (pre-commit hook)
     - Fails if skills.json drifts from RST
   * - Conciseness metrics
     - Per-commit (pre-submit test)
     - Fails if any skill > 200 tokens or average > 150
   * - Currency validation
     - Monthly (GitHub Actions CI)
     - Fails if any command is syntactically invalid

---

Next Steps
==========

Learn more about:

- :doc:`AGENTS` — Using skills in the development workflow
- :doc:`CONSTITUTION` § Architecture Boundaries — Understanding system constraints
- `.github/skills/breeze-contribution/decision_rules.json`_ — Formal decision logic for agents
- `scripts/ci/prek/extract_agent_skills.py`_ — How skill extraction works

Have questions? Ask in the `#airflow-dev <https://airflow.apache.org/community/get-help/>`_ Slack channel.
