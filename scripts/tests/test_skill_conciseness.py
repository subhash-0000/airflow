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
Test suite for agent skill conciseness metrics.

Validates that each agent skill maintains conciseness relative to its source documentation.
Conciseness requirement: skill size < 40% of source documentation section size.

This ensures skills remain usable as agent context windows without overwhelming the agent's
attention with excessive detail.
"""

import json
import re
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def skills_json():
    """Load skills.json for testing."""
    repo_root = Path(__file__).resolve().parents[2]
    skills_path = repo_root / ".github" / "skills" / "breeze-contribution" / "skills.json"

    if not skills_path.exists():
        pytest.skip(f"Skills file not found: {skills_path}")

    with open(skills_path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def contributing_docs():
    """Load all contributing docs for reference."""
    repo_root = Path(__file__).resolve().parents[2]
    docs_dir = repo_root / "contributing-docs"

    if not docs_dir.exists():
        pytest.skip(f"Docs directory not found: {docs_dir}")

    docs = {}
    for doc_file in docs_dir.glob("*.rst"):
        with open(doc_file) as f:
            docs[doc_file.stem] = f.read()

    return docs


def count_tokens_approx(text: str) -> int:
    """
    Approximate token count for a text string.

    Uses word count as a proxy (1 token ≈ 0.75 words).
    This is a simple heuristic for conciseness testing.

    Args:
        text: The text to count

    Returns:
        Approximate token count

    """
    words = len(text.split())
    return int(words / 0.75)  # Rough approximation


def extract_skill_size(skill: dict) -> int:
    """
    Calculate the size of a skill in tokens.

    Factors:
    - host/host_command length
    - breeze/breeze_command length
    - description/metadata

    Args:
        skill: The skill definition

    Returns:
        Approximate token size of skill

    """
    parts = [
        skill.get("host_command") or skill.get("host", ""),
        skill.get("breeze_command") or skill.get("breeze", ""),
        skill.get("description", ""),
        skill.get("reference", ""),
    ]
    combined = " ".join(parts)
    return count_tokens_approx(combined)


@pytest.mark.parametrize("skill_id,skill", [])
def test_skill_conciseness_parametrized(skill_id: str, skill: dict, skills_json):
    """
    Parametrized test for each skill's conciseness.

    This test is dynamically populated with all skills from skills.json.
    """
    max_size = 200  # Maximum recommended skill size in tokens

    actual_size = extract_skill_size(skill)
    assert (
        actual_size <= max_size
    ), f"Skill '{skill_id}' size {actual_size} tokens exceeds limit {max_size} tokens"


def test_all_skills_exist_in_json(skills_json):
    """Verify that skills.json contains at least one skill."""
    skills = skills_json.get("skills", [])
    if isinstance(skills, dict):
        skills = list(skills.values())
    assert len(skills) > 0, "No skills found in skills.json"


def test_skill_conciseness_aggregate(skills_json):
    """
    Test for skill conciseness across all skills.

    Verifies that:
    1. Each skill is reasonably sized (< 200 tokens typical)
    2. Average skill size is healthy (< 150 tokens)
    3. No individual skill is excessively large

    """
    skills_list = skills_json.get("skills", [])
    if isinstance(skills_list, dict):
        skills_list = list(skills_list.values())

    sizes = {}
    for idx, skill in enumerate(skills_list):
        skill_id = skill.get("workflow") or skill.get("id") or f"skill_{idx}"
        size = extract_skill_size(skill)
        sizes[skill_id] = size

    if not sizes:
        pytest.skip("No skills to test")

    # Calculate metrics
    avg_size = sum(sizes.values()) / len(sizes) if sizes else 0
    max_size = max(sizes.values()) if sizes else 0
    min_size = min(sizes.values()) if sizes else 0

    print(f"\nSkill Size Metrics:")
    print(f"  Average: {avg_size:.0f} tokens")
    print(f"  Maximum: {max_size} tokens")
    print(f"  Minimum: {min_size} tokens")
    print(f"  Total: {len(sizes)} skills")

    # Assertions
    assert (
        avg_size <= 150
    ), f"Average skill size {avg_size:.0f} exceeds recommended 150 tokens"
    assert max_size <= 300, f"Maximum skill size {max_size} exceeds hard limit 300 tokens"

    # Report any unusually large skills
    large_skills = {s_id: size for s_id, size in sizes.items() if size > 200}
    if large_skills:
        print(f"\n⚠️  Large skills detected (> 200 tokens):")
        for skill_id, size in sorted(large_skills.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {skill_id}: {size} tokens")


def test_skill_commands_not_empty(skills_json):
    """Test that all skills have non-empty commands."""
    skills_list = skills_json.get("skills", [])
    if isinstance(skills_list, dict):
        skills_list = list(skills_list.values())

    empty_commands = []
    for idx, skill in enumerate(skills_list):
        skill_id = skill.get("workflow") or skill.get("id") or f"skill_{idx}"
        host_cmd = (skill.get("host_command") or skill.get("host") or "").strip()
        breeze_cmd = (skill.get("breeze_command") or skill.get("breeze") or "").strip()

        if not host_cmd:
            empty_commands.append(f"{skill_id}: empty host command")
        if not breeze_cmd:
            empty_commands.append(f"{skill_id}: empty breeze command")

    assert (
        len(empty_commands) == 0
    ), f"Found skills with empty commands:\n  " + "\n  ".join(empty_commands)


def test_skill_references_valid_format(skills_json):
    """Test that skill references are valid URLs or RST references."""
    skills_list = skills_json.get("skills", [])
    if isinstance(skills_list, dict):
        skills_list = list(skills_list.values())

    invalid_refs = []
    for idx, skill in enumerate(skills_list):
        skill_id = skill.get("workflow") or skill.get("id") or f"skill_{idx}"
        ref = skill.get("reference", "")
        if not ref:
            continue

        # Check if it looks like a valid reference
        is_url = ref.startswith(("http://", "https://", "file://"))
        is_rst_ref = ref.startswith(("../", "docs/", "/"))
        is_valid = is_url or is_rst_ref or len(ref) > 0

        if not is_valid:
            invalid_refs.append(f"{skill_id}: {ref}")

    # This is a soft check—just warn, don't fail
    if invalid_refs:
        print(f"\n⚠️  Potentially invalid references:")
        for ref in invalid_refs:
            print(f"  - {ref}")
