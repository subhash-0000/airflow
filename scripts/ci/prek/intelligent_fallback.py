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
Intelligent Fallback — Breeze-Aware Command Selection with 3-Tier Decision Layer

Implements @potiuk's guidance from issue #62500:
> "NOT EVERYTHING should be done with breeze... In vast majority of cases
> `uv run --project distribution_folder pytest` is enough. Only when this
> fails because some system dependency is missing should we fall back to breeze."

This module provides ERROR-DRIVEN fallback logic, not just context-driven.

Key Differentiator:
- Most POCs: if inside_breeze → breeze_cmd, else → host_cmd
- This implementation: Try native first, fallback based on ERROR TYPE

3-Tier Decision Chain:
1. Tier 1 (NATIVE): uv run — Fastest, IDE-debuggable, preferred
2. Tier 2 (BREEZE): breeze run — Has all system dependencies
3. Tier 3 (SYSTEM): breeze start-airflow — Full system verification

Usage:
    from intelligent_fallback import (
        get_command_with_fallback,
        should_fallback_to_breeze,
        CommandTier,
        CommandDecision,
    )

    # Get command with intelligent fallback
    decision = get_command_with_fallback(
        workflow="run-tests",
        test_path="tests/test_example.py",
        distribution_folder="airflow-core",
    )

    print(f"Tier: {decision.tier.value}")
    print(f"Command: {decision.command}")
    print(f"Reason: {decision.reason}")

    # If command fails, check if should fallback
    if not result.success and should_fallback_to_breeze(result.stderr):
        # Use Breeze instead
        breeze_decision = get_command_with_fallback(..., force_breeze=True)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class CommandTier(Enum):
    """
    3-tier command execution strategy.

    Attributes:
        NATIVE: uv run on host (fastest, IDE-debuggable) — PREFERRED
        BREEZE: breeze run in container (has all deps) — FALLBACK
        SYSTEM: breeze start-airflow (full verification) — COMPLEX CHANGES
    """
    NATIVE = "native"
    BREEZE = "breeze"
    SYSTEM = "system"


@dataclass
class CommandDecision:
    """
    Result of intelligent command selection.

    Attributes:
        command: The actual command string to execute
        tier: Which tier was selected (NATIVE, BREEZE, or SYSTEM)
        reason: Human-readable explanation for why this tier was chosen
        fallback_available: Whether fallback to next tier is possible
        workflow: The workflow name this decision is for
    """
    command: str
    tier: CommandTier
    reason: str
    fallback_available: bool = True
    workflow: str = ""

    def to_dict(self) -> dict[str, str | bool]:
        """Convert to dictionary for JSON serialization."""
        return {
            "command": self.command,
            "tier": self.tier.value,
            "reason": self.reason,
            "fallback_available": self.fallback_available,
            "workflow": self.workflow,
        }


# System dependency error patterns that trigger Breeze fallback
SYSTEM_DEP_PATTERNS = [
    # Database drivers
    "mysqlclient requires MySQL C libraries",
    "mysql_config not found",
    "libmysqlclient",
    "libpq.so not found",
    "libpq.dylib not found",
    "postgresql",
    "psycopg2",
    # System libraries
    "system dependency",
    "shared library",
    ".so not found",
    ".dylib not found",
    "DLL load failed",
    # Missing tools
    "npm not found",
    "node not found",
    # Permission/access issues
    "permission denied",
    "access denied",
    # Build/wheel errors (often indicate missing system deps)
    "could not build wheels",
    "failed building wheel",
]


def should_fallback_to_breeze(error_output: str) -> bool:
    """
    Determine if an error indicates missing system dependencies.

    This implements ERROR-DRIVEN fallback logic:
    - Analyzes stderr output from failed native command
    - Returns True if error suggests system dependencies are missing
    - Agent should then retry with Breeze (which has all deps)

    Args:
        error_output: stderr output from failed command

    Returns:
        True if should fallback to Breeze, False otherwise

    Examples:
        >>> should_fallback_to_breeze("mysqlclient requires MySQL C libraries")
        True
        >>> should_fallback_to_breeze("test failed: assertion error")
        False
        >>> should_fallback_to_breeze("libpq.so not found")
        True
    """
    error_lower = error_output.lower()

    # Check for explicit system dependency errors
    for pattern in SYSTEM_DEP_PATTERNS:
        if pattern.lower() in error_lower:
            return True

    # Check for compilation errors (often indicates missing dev libraries)
    compilation_indicators = [
        "compilation failed",
        "build failed",
        "unable to find",
        "cannot find",
        "no such file or directory",
    ]
    for indicator in compilation_indicators:
        if indicator in error_lower:
            # Could be system dep issue, but not certain
            # Agent may want to try Breeze as diagnostic step
            pass

    return False


def is_system_level_change(
    test_path: str | None = None,
    workflow: str = "",
) -> bool:
    """
    Heuristic to detect if a change requires full system verification.

    Tier 3 (SYSTEM) is used for complex changes that affect multiple
    Airflow components. This is a stretch goal / nice-to-have.

    Args:
        test_path: Path to test file being run
        workflow: Workflow name

    Returns:
        True if system-level verification is recommended

    Examples of system-level changes:
        - Dag execution end-to-end
        - Scheduler/triggerer behavior
        - Integration tests with external systems
        - API endpoint changes
    """
    if not test_path:
        return False

    test_path_lower = test_path.lower()

    # System-level test patterns
    system_patterns = [
        "system",
        "integration",
        "e2e",
        "end_to_end",
        "scheduler",
        "triggerer",
        "api_server",
        "dag_run",
        "task_instance",
    ]

    return any(pattern in test_path_lower for pattern in system_patterns)


def get_command_with_fallback(
    workflow: str,
    test_path: str | None = None,
    distribution_folder: str = "airflow-core",
    force_breeze: bool = False,
    force_tier: CommandTier | None = None,
) -> CommandDecision:
    """
    Get command with intelligent 3-tier fallback logic.

    This is the main API that agents call. It implements @potiuk's guidance:
    1. Try NATIVE first (fastest, IDE-debuggable)
    2. Fallback to BREEZE only if system deps missing
    3. Use SYSTEM for complex integration tests

    Args:
        workflow: Workflow name (e.g., 'run-tests', 'static-checks')
        test_path: Optional test path to substitute in command
        distribution_folder: Distribution folder for uv run (default: airflow-core)
        force_breeze: If True, skip to BREEZE tier immediately
        force_tier: If set, use specific tier regardless of logic

    Returns:
        CommandDecision with command, tier, reason, and fallback info

    Examples:
        # Normal case — native preferred
        >>> decision = get_command_with_fallback('run-tests', 'tests/test.py')
        >>> decision.tier
        <CommandTier.NATIVE: 'native'>
        >>> decision.reason
        'Native execution preferred for speed and IDE debugging'

        # Force Breeze (e.g., after native failed)
        >>> decision = get_command_with_fallback('run-tests', force_breeze=True)
        >>> decision.tier
        <CommandTier.BREEZE: 'breeze'>

        # Static checks — always native (prek runs on host)
        >>> decision = get_command_with_fallback('static-checks')
        >>> decision.tier
        <CommandTier.NATIVE: 'native'>
    """
    # Override: force specific tier
    if force_tier is not None:
        return _get_command_for_tier(
            force_tier,
            workflow,
            test_path,
            distribution_folder,
            reason=f"Forced to {force_tier.value} tier",
        )

    # Override: force Breeze (common after native fails)
    if force_breeze:
        return _get_command_for_tier(
            CommandTier.BREEZE,
            workflow,
            test_path,
            distribution_folder,
            reason="Breeze execution requested (e.g., after native failure)",
        )

    # Workflow-specific logic
    if workflow == "static-checks":
        # Static checks (prek) always run on host — no Docker needed
        return _get_command_for_tier(
            CommandTier.NATIVE,
            workflow,
            test_path=None,
            distribution_folder=None,
            reason="prek runs on host natively (no Docker needed)",
        )

    if workflow == "run-tests":
        # Tests: prefer native (faster, IDE-debuggable)
        # Fallback to Breeze if system deps missing
        return _get_command_for_tier(
            CommandTier.NATIVE,
            workflow,
            test_path,
            distribution_folder,
            reason="Native execution preferred for speed and IDE debugging",
        )

    if workflow == "system-verify":
        # System verification — may need full Airflow stack
        if is_system_level_change(test_path, workflow):
            return _get_command_for_tier(
                CommandTier.SYSTEM,
                workflow,
                test_path,
                distribution_folder,
                reason="System-level change detected — full verification needed",
            )
        else:
            return _get_command_for_tier(
                CommandTier.BREEZE,
                workflow,
                test_path,
                distribution_folder,
                reason="Standard system verification",
            )

    if workflow == "create-pr-description":
        # Git operations always run on host
        return _get_command_for_tier(
            CommandTier.NATIVE,
            workflow,
            test_path=None,
            distribution_folder=None,
            reason="Git operations run on host natively",
        )

    # Default: prefer native
    return _get_command_for_tier(
        CommandTier.NATIVE,
        workflow,
        test_path,
        distribution_folder,
        reason="Default to native execution",
    )


def _get_command_for_tier(
    tier: CommandTier,
    workflow: str,
    test_path: str | None,
    distribution_folder: str | None,
    reason: str,
) -> CommandDecision:
    """
    Get command for a specific tier.

    Internal helper that builds the actual command string.

    Args:
        tier: Which tier to use
        workflow: Workflow name
        test_path: Optional test path
        distribution_folder: Optional distribution folder
        reason: Human-readable reason for tier selection

    Returns:
        CommandDecision with populated command
    """
    # Build command based on tier and workflow
    if tier == CommandTier.NATIVE:
        command = _build_native_command(workflow, test_path, distribution_folder)
        fallback_available = (workflow != "static-checks")  # Can fallback from tests, not prek
    elif tier == CommandTier.BREEZE:
        command = _build_breeze_command(workflow, test_path)
        fallback_available = True  # Could potentially go to SYSTEM
    elif tier == CommandTier.SYSTEM:
        command = _build_system_command(workflow, test_path)
        fallback_available = False  # Already at highest tier
    else:
        command = f"echo 'Unknown tier: {tier}'"
        fallback_available = False

    return CommandDecision(
        command=command,
        tier=tier,
        reason=reason,
        fallback_available=fallback_available,
        workflow=workflow,
    )


def _build_native_command(
    workflow: str,
    test_path: str | None,
    distribution_folder: str | None,
) -> str:
    """Build command for NATIVE tier execution."""
    if workflow == "run-tests":
        dist = distribution_folder or "airflow-core"
        path = test_path or ""
        return f"uv run --project {dist} pytest {path} -xvs"

    if workflow == "static-checks":
        return "prek run --from-ref main --stage pre-commit"

    if workflow == "create-pr-description":
        return "git status && git diff --stat"

    return f"echo 'Unknown workflow: {workflow}'"


def _build_breeze_command(
    workflow: str,
    test_path: str | None,
) -> str:
    """Build command for BREEZE tier execution."""
    if workflow == "run-tests":
        path = test_path or ""
        return f"breeze run pytest {path} -xvs"

    if workflow == "static-checks":
        return "breeze run prek --from-ref main --stage pre-commit"

    if workflow == "system-verify":
        return "breeze run airflow info"

    if workflow == "create-pr-description":
        return "git status && git diff --stat"

    return f"echo 'Unknown workflow: {workflow}'"


def _build_system_command(
    workflow: str,
    test_path: str | None,
) -> str:
    """Build command for SYSTEM tier execution (full Airflow stack)."""
    if workflow == "system-verify":
        # Start full Airflow stack for integration testing
        return "breeze start-airflow --integration"

    # Fallback to breeze command for other workflows
    return _build_breeze_command(workflow, test_path)


def get_fallback_command(
    original_decision: CommandDecision,
    error_output: str,
    test_path: str | None = None,
    distribution_folder: str = "airflow-core",
) -> CommandDecision | None:
    """
    Get fallback command based on error type.

    This implements the error-driven decision logic:
    - If error indicates system deps missing → fallback to BREEZE
    - If error is test failure → don't fallback (show to user)
    - If error is permission issue → suggest fix or fallback

    Args:
        original_decision: The original command decision that failed
        error_output: stderr output from failed command
        test_path: Optional test path
        distribution_folder: Optional distribution folder

    Returns:
        CommandDecision for fallback command, or None if no fallback recommended

    Examples:
        # System dep error → fallback to Breeze
        >>> original = get_command_with_fallback('run-tests', 'tests/test.py')
        >>> fallback = get_fallback_command(original, 'libpq.so not found')
        >>> fallback.tier
        <CommandTier.BREEZE: 'breeze'>

        # Test failure → no fallback (show to user)
        >>> fallback = get_fallback_command(original, 'AssertionError: test failed')
        >>> fallback is None
        True
    """
    workflow = original_decision.workflow

    # Check if should fallback to Breeze
    if should_fallback_to_breeze(error_output):
        return get_command_with_fallback(
            workflow,
            test_path=test_path,
            distribution_folder=distribution_folder,
            force_breeze=True,
        )

    # Check if should go to SYSTEM tier
    if is_system_level_change(test_path, workflow):
        if original_decision.tier != CommandTier.SYSTEM:
            return get_command_with_fallback(
                workflow,
                test_path=test_path,
                distribution_folder=distribution_folder,
                force_tier=CommandTier.SYSTEM,
            )

    # No fallback recommended — error is likely a test failure or other issue
    return None


def main():
    """CLI entry point for testing intelligent fallback."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Intelligent Fallback — Get commands with 3-tier fallback logic",
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
        help="Workflow name (e.g., run-tests, static-checks)",
    )
    parser.add_argument(
        "--test-path",
        help="Test path to substitute in command",
    )
    parser.add_argument(
        "--dist",
        default="airflow-core",
        help="Distribution folder for uv run (default: airflow-core)",
    )
    parser.add_argument(
        "--force-breeze",
        action="store_true",
        help="Force Breeze execution (skip native)",
    )
    parser.add_argument(
        "--force-tier",
        choices=["native", "breeze", "system"],
        help="Force specific tier",
    )
    parser.add_argument(
        "--check-error",
        help="Check if an error should trigger fallback",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()

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

    # Require workflow argument
    if not args.workflow:
        parser.error("Workflow argument is required (or use --check-error)")

    # Get command with fallback logic
    force_tier = None
    if args.force_tier:
        force_tier = CommandTier(args.force_tier)

    decision = get_command_with_fallback(
        args.workflow,
        test_path=args.test_path,
        distribution_folder=args.dist,
        force_breeze=args.force_breeze,
        force_tier=force_tier,
    )

    # Output result
    if args.json:
        print(json.dumps(decision.to_dict(), indent=2))
    else:
        print(f"Workflow: {decision.workflow}")
        print(f"Tier: {decision.tier.value}")
        print(f"Command: {decision.command}")
        print(f"Reason: {decision.reason}")
        print(f"Fallback Available: {decision.fallback_available}")


if __name__ == "__main__":
    main()
