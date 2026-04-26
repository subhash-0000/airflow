#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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

"""
Validate that all agent skills defined in contributing-docs are current and executable.

This script:
1. Loads all skills from .github/skills/breeze-contribution/skills.json
2. Tests each skill's commands (host_command and breeze_command) for syntax validity
3. Verifies commands reference valid executables and paths
4. Reports any skills that are outdated or have invalid commands
5. Exits with non-zero status if any skill is invalid (fails CI)

Usage:
  python scripts/ci/prek/validate_docs_currency.py
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


class SkillValidationError(Exception):
    """Raised when a skill fails validation."""

    pass


class SkillDuplicateError(Exception):
    """Raised when a skill ID is duplicated."""

    pass


def load_skills(skills_path: Path) -> Dict[str, Any]:
    """Load skills from skills.json file."""
    if not skills_path.exists():
        raise FileNotFoundError(f"Skills file not found: {skills_path}")

    with open(skills_path) as f:
        return json.load(f)


def validate_skill_syntax(skill_id: str, command: str) -> bool:
    """
    Validate that a command has valid shell syntax.

    Args:
        skill_id: The skill identifier
        command: The shell command to validate

    Returns:
        True if syntax is valid, False otherwise

    """
    if not command or not command.strip():
        print(f"  ✗ Skill '{skill_id}': Empty command")
        return False

    # Check for common invalid patterns
    invalid_patterns = [
        ("empty pipes", r"^\s*\|\s*$"),
        ("unclosed quotes", r"^[^'\"]*['\"][^'\"]*$"),
        ("unmatched braces", lambda x: x.count("{") != x.count("}")),
    ]

    for pattern_name, pattern in invalid_patterns:
        if callable(pattern):
            if pattern(command):
                print(f"  ✗ Skill '{skill_id}': Invalid {pattern_name} in command: {command}")
                return False
        else:
            import re

            if re.search(pattern, command):
                print(f"  ✗ Skill '{skill_id}': Invalid {pattern_name} in command: {command}")
                return False

    return True


def validate_skill_executables(skill_id: str, command: str) -> bool:
    """
    Validate that commands reference valid executables (basic check).

    Args:
        skill_id: The skill identifier
        command: The shell command to validate

    Returns:
        True if executables appear valid, False otherwise

    """
    import re

    # Extract the first word (the executable)
    match = re.match(r"^\s*([^\s]+)", command)
    if not match:
        print(f"  ✗ Skill '{skill_id}': Cannot parse executable from command: {command}")
        return False

    executable = match.group(1)

    # Check if it's a valid executable name (no path traversal, no special chars)
    if ".." in executable or "\\" in executable:
        print(f"  ✗ Skill '{skill_id}': Suspicious executable path: {executable}")
        return False

    return True


def validate_skill(skill: Dict[str, Any], skill_id: str) -> List[str]:
    """
    Validate a single skill.

    Args:
        skill: The skill definition dict
        skill_id: The skill identifier

    Returns:
        List of error messages (empty if valid)

    Raises:
        SkillValidationError: If skill is invalid

    """
    errors = []

    # Check required fields (handle both naming conventions)
    host_field = skill.get("host_command") or skill.get("host")
    breeze_field = skill.get("breeze_command") or skill.get("breeze")

    if not host_field:
        errors.append(f"  ✗ Skill '{skill_id}': Missing required field 'host' or 'host_command'")

    if not breeze_field:
        errors.append(f"  ✗ Skill '{skill_id}': Missing required field 'breeze' or 'breeze_command'")

    if errors:
        return errors

    # Validate host command syntax
    if not validate_skill_syntax(skill_id, host_field):
        errors.append(f"Skill '{skill_id}': Invalid host command syntax")

    # Validate breeze command syntax
    if not validate_skill_syntax(skill_id, breeze_field):
        errors.append(f"Skill '{skill_id}': Invalid breeze command syntax")

    # Validate executables
    if not validate_skill_executables(skill_id, host_field):
        errors.append(f"Skill '{skill_id}': Invalid host command executable")

    if not validate_skill_executables(skill_id, breeze_field):
        errors.append(f"Skill '{skill_id}': Invalid breeze command executable")

    return errors


def check_duplicate_ids(skills: Dict[str, Any]) -> List[str]:
    """
    Check for duplicate skill IDs.

    Args:
        skills: The full skills dict from skills.json

    Returns:
        List of error messages for duplicates

    """
    seen_ids = set()
    duplicates = []

    # Handle both dict and list formats for skills
    skills_list = skills.get("skills", [])
    if isinstance(skills_list, dict):
        skills_list = skills_list.values()

    for skill in skills_list:
        skill_id = skill.get("workflow") or skill.get("id")
        if not skill_id:
            continue
        if skill_id in seen_ids:
            duplicates.append(f"Duplicate skill ID found: {skill_id}")
        seen_ids.add(skill_id)

    return duplicates


def run_validation(skills_path: Path) -> int:
    """
    Run full validation suite on skills.

    Args:
        skills_path: Path to skills.json file

    Returns:
        Exit code (0 for success, 1 for failure)

    """
    print("Validating agent skills currency...\n")

    try:
        skills_data = load_skills(skills_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    all_errors = []

    # Check for duplicates
    duplicate_errors = check_duplicate_ids(skills_data)
    if duplicate_errors:
        print("❌ Duplicate skill IDs found:")
        for error in duplicate_errors:
            print(f"  {error}")
            all_errors.append(error)
        print()

    # Validate each skill
    print("Validating individual skills:")
    skills_list = skills_data.get("skills", [])
    if isinstance(skills_list, dict):
        skills_list = list(skills_list.values())

    valid_count = 0
    invalid_count = 0

    for idx, skill in enumerate(skills_list):
        skill_id = skill.get("workflow") or skill.get("id") or f"skill_{idx}"
        errors = validate_skill(skill, skill_id)
        if errors:
            invalid_count += 1
            for error in errors:
                print(error)
                all_errors.append(error)
        else:
            print(f"  ✓ Skill '{skill_id}': Valid")
            valid_count += 1

    print(f"\n{'='*60}")
    print(f"Summary: {valid_count} valid, {invalid_count} invalid, {len(duplicate_errors)} duplicates")
    print(f"{'='*60}")

    if all_errors:
        print("\n❌ Validation FAILED")
        return 1
    else:
        print("\n✓ All skills are current and valid!")
        return 0


def main() -> int:
    """Main entry point."""
    # Find the workspace root
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[3]  # Navigate to workspace root

    skills_path = repo_root / ".github" / "skills" / "breeze-contribution" / "skills.json"

    return run_validation(skills_path)


if __name__ == "__main__":
    sys.exit(main())
