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
Runtime context detection for Breeze agent skills with intelligent fallback.

This module provides callable code that agents execute at runtime to detect
their current execution context and receive the correct command for their
actual context.

IMPLEMENTS 3-TIER INTELLIGENT FALLBACK (per @potiuk's guidance in #62500):
1. Tier 1 (NATIVE): uv run — Fastest, IDE-debuggable, PREFERRED
2. Tier 2 (BREEZE): breeze run — Has all system dependencies, FALLBACK
3. Tier 3 (SYSTEM): breeze start-airflow — Full system verification

KEY DIFFERENTIATOR:
- Most POCs: if inside_breeze → breeze_cmd, else → host_cmd
- This implementation: ERROR-DRIVEN fallback, not just context-driven

Priority chain for context detection:
1. AIRFLOW_BREEZE_CONTAINER env var
2. /.dockerenv file exists
3. /opt/airflow directory exists

Agents call get_command('run-tests', test_path='...') and receive the
correct command with intelligent fallback logic.

Usage:
    from breeze_context_detect import get_command, is_inside_breeze

    # Detect context
    if is_inside_breeze():
        print("Running inside Breeze container")
    else:
        print("Running on host")

    # Get command for context (with intelligent fallback)
    cmd = get_command('run-tests', test_path='tests/unit/test_foo.py')
    print(f"Run: {cmd['command']}")
    print(f"Tier: {cmd.get('tier', 'native')}")
    print(f"Reason: {cmd.get('reason', 'default')}")
"""

import os
import json
from pathlib import Path
from typing import TypedDict, Any

# Canonical path to skills.json
SKILLS_JSON = Path(".github/skills/breeze-contribution/skills.json")

# Import intelligent fallback for 3-tier decision logic
from intelligent_fallback import (
    CommandDecision,
    CommandTier,
    get_command_with_fallback,
    should_fallback_to_breeze,
    get_fallback_command,
)


class CommandResult(TypedDict, total=False):
    """Result from get_command() with context-aware command selection."""
    context: str  # "host" or "breeze"
    command: str  # The command to execute
    workflow: str  # The workflow name
    tier: str  # "native", "breeze", or "system"
    reason: str  # Why this tier was selected
    fallback_available: bool  # Whether fallback is available
    error_driven: bool  # Whether error triggered fallback


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
    force_breeze: bool = False,
    error_output: str | None = None,
) -> CommandResult:
    """
    Get the correct command for a workflow with intelligent 3-tier fallback.

    This implements @potiuk's guidance from issue #62500:
    - Try native (uv run) first — faster, IDE-debuggable
    - Fallback to breeze only if system deps missing
    - Error-driven decisions, not just context-driven

    Args:
        workflow: The workflow name (e.g., 'run-tests', 'static-checks')
        test_path: Optional test path to substitute in command template
        distribution_folder: Optional distribution folder for uv run
        force_breeze: If True, skip to BREEZE tier immediately
        error_output: Optional error output from previous command (for fallback)

    Returns:
        CommandResult dict with context, command, workflow, tier, reason, etc.

    Raises:
        ValueError: If workflow is not supported

    Examples:
        # Normal case — native preferred
        >>> result = get_command('run-tests', 'tests/test.py')
        >>> result['tier']
        'native'
        >>> result['reason']
        'Native execution preferred for speed and IDE debugging'

        # After native fails with system dep error
        >>> result = get_command('run-tests', error_output='libpq.so not found')
        >>> result['tier']
        'breeze'
    """
    # If error output provided, check if should fallback
    if error_output and should_fallback_to_breeze(error_output):
        force_breeze = True

    # Get command with intelligent fallback
    decision = get_command_with_fallback(
        workflow,
        test_path=test_path,
        distribution_folder=distribution_folder or "airflow-core",
        force_breeze=force_breeze,
    )

    # Detect context
    inside_breeze = is_inside_breeze()
    context = "breeze" if inside_breeze else "host"

    # Build result with extended fields
    return CommandResult(
        context=context,
        command=decision.command,
        workflow=workflow,
        tier=decision.tier.value,
        reason=decision.reason,
        fallback_available=decision.fallback_available,
        error_driven=error_output is not None,
    )


def main():
    """CLI entry point for testing context detection with intelligent fallback."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect Breeze context and get commands with intelligent fallback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get command for run-tests workflow
  %(prog)s run-tests --test-path tests/test_example.py

  # Force Breeze execution
  %(prog)s run-tests --force-breeze

  # Check if error should trigger fallback
  %(prog)s --check-error "libpq.so not found"

  # Output as JSON
  %(prog)s run-tests --json
        """,
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
        default="airflow-core",
        help="Distribution folder for uv run (default: airflow-core)"
    )
    parser.add_argument(
        "--force-breeze",
        action="store_true",
        help="Force Breeze execution (skip native tier)"
    )
    parser.add_argument(
        "--check-error",
        help="Check if an error string should trigger fallback to Breeze"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    args = parser.parse_args()

    # Detect context
    inside = is_inside_breeze()

    # Special case: check error string
    if args.check_error:
        should_fallback = should_fallback_to_breeze(args.check_error)
        result = {
            "error": args.check_error,
            "should_fallback_to_breeze": should_fallback,
        }
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {args.check_error}")
            print(f"Should fallback to Breeze: {should_fallback}")
        return

    if args.workflow:
        # Get command for workflow with intelligent fallback
        result = get_command(
            args.workflow,
            test_path=args.test_path,
            distribution_folder=args.dist,
            force_breeze=args.force_breeze,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Context: {result['context']}")
            print(f"Workflow: {result['workflow']}")
            print(f"Tier: {result.get('tier', 'native')}")
            print(f"Command: {result['command']}")
            print(f"Reason: {result.get('reason', 'default')}")
            print(f"Fallback Available: {result.get('fallback_available', False)}")
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
