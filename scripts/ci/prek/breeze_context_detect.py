# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

"""
Runtime context detection for Breeze agent skills.

This module provides callable code that agents execute at runtime to detect
their current execution context and receive the correct command for their
actual context.

Priority chain:
1. AIRFLOW_BREEZE_CONTAINER env var
2. /.dockerenv file exists
3. /opt/airflow directory exists

Agents call get_command('run-tests', test_path='...') and receive the
correct command for their actual context.

Usage:
    from breeze_context_detect import get_command, is_inside_breeze

    # Detect context
    if is_inside_breeze():
        print("Running inside Breeze container")
    else:
        print("Running on host")

    # Get command for context
    cmd = get_command('run-tests', test_path='tests/unit/test_foo.py')
    print(f"Run: {cmd['command']}")
"""

import os
import json
from pathlib import Path
from typing import TypedDict

# Canonical path to skills.json
SKILLS_JSON = Path(".github/skills/breeze-contribution/skills.json")


class CommandResult(TypedDict):
    """Type definition for command result."""
    context: str
    command: str
    workflow: str


def is_inside_breeze() -> bool:
    """
    Detect if running inside Breeze container.

    Priority chain:
    1. AIRFLOW_BREEZE_CONTAINER env var
    2. /.dockerenv file exists
    3. /opt/airflow directory exists

    Returns:
        True if inside Breeze container, False otherwise
    """
    # Priority 1: Check explicit env var
    if os.getenv("AIRFLOW_BREEZE_CONTAINER") == "1":
        return True

    # Priority 2: Check Docker marker
    if Path("/.dockerenv").exists():
        return True

    # Priority 3: Check Breeze mount point
    if Path("/opt/airflow").exists():
        return True

    return False


def _load_skills() -> dict:
    """Load skills from skills.json."""
    if not SKILLS_JSON.exists():
        raise FileNotFoundError(
            f"{SKILLS_JSON} not found. Run extract_agent_skills.py first."
        )
    return json.loads(SKILLS_JSON.read_text(encoding="utf-8"))


def get_command(
    workflow: str,
    test_path: str | None = None,
    distribution_folder: str | None = None,
) -> CommandResult:
    """
    Get the correct command for a workflow based on current context.

    Args:
        workflow: The workflow name (e.g., 'run-tests', 'static-checks')
        test_path: Optional test path to substitute in command template
        distribution_folder: Optional distribution folder for uv run

    Returns:
        CommandResult dict with context, command, and workflow

    Raises:
        ValueError: If workflow is not found in skills.json
    """
    skills = _load_skills()

    # Find the workflow
    skill = None
    for s in skills.get("skills", []):
        if s["workflow"] == workflow:
            skill = s
            break

    if skill is None:
        available = [s["workflow"] for s in skills.get("skills", [])]
        raise ValueError(
            f"Unknown workflow: {workflow}. Available: {available}"
        )

    # Detect context
    inside_breeze = is_inside_breeze()
    context = "breeze" if inside_breeze else "host"

    # Select command based on context
    if inside_breeze:
        command_template = skill.get("breeze", "")
    else:
        command_template = skill.get("host", "")

    # Substitute placeholders
    if test_path:
        command_template = command_template.replace("{path}", test_path)
        command_template = command_template.replace("{test_path}", test_path)
    if distribution_folder:
        command_template = command_template.replace("{dist}", distribution_folder)

    return CommandResult(
        context=context,
        command=command_template,
        workflow=workflow,
    )


def main():
    """CLI entry point for testing context detection."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect Breeze context and get commands"
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        help="Workflow name (e.g., run-tests, static-checks)"
    )
    parser.add_argument(
        "--test-path",
        help="Test path to substitute in command"
    )
    parser.add_argument(
        "--dist",
        help="Distribution folder for uv run"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    args = parser.parse_args()

    # Detect context
    inside = is_inside_breeze()

    if args.workflow:
        # Get command for workflow
        result = get_command(
            args.workflow,
            test_path=args.test_path,
            distribution_folder=args.dist,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Context: {result['context']}")
            print(f"Workflow: {result['workflow']}")
            print(f"Command: {result['command']}")
    else:
        # Just show context
        if args.json:
            print(json.dumps({
                "inside_breeze": inside,
                "context": "breeze" if inside else "host",
            }, indent=2))
        else:
            print(f"Running inside Breeze: {inside}")
            print(f"Context: {'breeze' if inside else 'host'}")


if __name__ == "__main__":
    main()
