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
Extract agent skill definitions from contributing-docs/*.rst files.

This script parses RST directives in the form:

    .. agent-skill:: workflow-name
       :host: command-to-run-on-host
       :breeze: command-to-run-in-breeze
       :fallback_condition: when-to-fallback

The source of truth is the contributing documentation files. This ensures
that skills and human-readable docs are always in sync — they're the same file.

This script mirrors the pattern used by update-breeze-cmd-output (line 909 of
.pre-commit-config.yaml): a prek hook reads a source file, generates a derived
artifact, and fails CI if the committed artifact diverges from what was just generated.

Usage:
    # Generate/update skills.json:
    python3 scripts/ci/prek/extract_agent_skills.py

    # Check for drift only (CI mode — exits 1 if drift detected):
    python3 scripts/ci/prek/extract_agent_skills.py --check
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Canonical paths — relative to repo root
CONTRIBUTING_DOCS_DIR = Path("contributing-docs")
SKILLS_JSON = Path(".github/skills/breeze-contribution/skills.json")


def parse_rst_file(content: str) -> list[dict[str, str]]:
    """
    Parse RST content and extract all agent-skill directives.

    Returns a list of skill dicts, one per directive found.
    """
    skills = []
    lines = content.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for agent-skill directive
        match = re.match(r"^\.\. agent-skill::\s+(\S+)", line)
        if match:
            workflow_name = match.group(1)
            skill = {"workflow": workflow_name}
            i += 1

            # Parse options (indented lines starting with :option:)
            while i < len(lines):
                option_line = lines[i]
                # Options are indented and start with :
                option_match = re.match(r"^\s+:(\w+):\s*(.+?)\s*$", option_line)
                if option_match:
                    key = option_match.group(1)
                    value = option_match.group(2).strip()
                    skill[key] = value
                    i += 1
                else:
                    # End of options
                    break

            skills.append(skill)
        else:
            i += 1

    return skills


def extract_skills_from_file(rst_path: Path) -> list[dict[str, str]]:
    """
    Read an RST file and extract all agent-skill directives.

    Returns a list of skill dicts.
    """
    if not rst_path.exists():
        return []

    content = rst_path.read_text(encoding="utf-8")
    return parse_rst_file(content)


def extract_all_skills() -> list[dict[str, str]]:
    """
    Scan all contributing-docs/*.rst files and extract agent skills.

    Returns a list of all skill dicts found.
    """
    if not CONTRIBUTING_DOCS_DIR.exists():
        print(
            f"ERROR: {CONTRIBUTING_DOCS_DIR} not found. Run from repo root.",
            file=sys.stderr,
        )
        sys.exit(1)

    all_skills = []

    # Scan all .rst files in contributing-docs/
    for rst_file in CONTRIBUTING_DOCS_DIR.glob("*.rst"):
        skills = extract_skills_from_file(rst_file)
        for skill in skills:
            skill["source_file"] = str(rst_file)
            all_skills.append(skill)

    return all_skills


def build_skills_json(skills: list[dict[str, str]]) -> dict:
    """Build the full skills.json structure from extracted skill dicts."""
    # Define fallback patterns for error-driven decision making
    # These patterns are used by intelligent_fallback.py to detect system dependency errors
    fallback_patterns = [
        "mysqlclient requires MySQL C libraries",
        "mysql_config not found",
        "libmysqlclient",
        "libpq.so not found",
        "libpq.dylib not found",
        "postgresql",
        "psycopg2",
        "system dependency",
        "shared library",
        ".so not found",
        ".dylib not found",
        "DLL load failed",
        "npm not found",
        "node not found",
    ]

    # Define tier mapping based on workflow type
    tier_mapping = {
        "static-checks": ("native", "prek runs on host natively (no Docker needed)"),
        "run-tests": ("native", "Native execution preferred for speed and IDE debugging"),
        "system-verify": ("system", "System-level verification requires full Airflow stack"),
        "create-pr-description": ("native", "Git operations run on host natively"),
    }

    return {
        "$schema": "breeze-agent-skills/v1",
        "source": "contributing-docs/*.rst",
        "description": (
            "Auto-generated from .. agent-skill:: directives in contributing-docs/*.rst. "
            "Do not edit manually — update the RST files instead."
        ),
        "fallback_patterns": fallback_patterns,
        "skills": [
            {
                "workflow": s["workflow"],
                "host": s.get("host", ""),
                "breeze": s.get("breeze", ""),
                "fallback_condition": s.get("fallback_condition", s.get("fallback", "never")),
                "tier": s.get("tier", tier_mapping.get(s["workflow"], ("native", "default"))[0]),
                "tier_reason": s.get("tier_reason", tier_mapping.get(s["workflow"], ("native", "default"))[1]),
                "source_file": s.get("source_file", ""),
            }
            for s in skills
        ],
    }


def write_skills_json(data: dict, output_path: Path) -> None:
    """Write skills dict to JSON file with stable formatting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def check_drift(generated: dict, existing_path: Path) -> bool:
    """
    Returns True if drift is detected (committed file differs from generated).
    Returns False if they match.
    """
    if not existing_path.exists():
        print(f"DRIFT: {existing_path} does not exist but should be generated.", file=sys.stderr)
        return True

    committed = json.loads(existing_path.read_text(encoding="utf-8"))

    # Compare only the skills list — ignore metadata fields like description
    if committed.get("skills") != generated.get("skills"):
        print("DRIFT DETECTED: committed skills.json does not match contributing-docs/*.rst.", file=sys.stderr)
        print("Run: python3 scripts/ci/prek/extract_agent_skills.py", file=sys.stderr)
        print("Then commit the updated skills.json.", file=sys.stderr)
        return True

    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract agent skills from contributing-docs/*.rst and write/validate skills.json"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: exit 1 if committed skills.json differs from contributing-docs/*.rst (for CI)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SKILLS_JSON,
        help=f"Path to output skills.json (default: {SKILLS_JSON})",
    )
    args = parser.parse_args()

    skills = extract_all_skills()

    if not skills:
        print(
            "WARNING: No .. agent-skill:: directives found in contributing-docs/*.rst.",
            file=sys.stderr,
        )
        sys.exit(0)

    generated = build_skills_json(skills)

    if args.check:
        drift = check_drift(generated, args.output)
        if drift:
            sys.exit(1)
        print(f"OK: {args.output} is in sync with contributing-docs/*.rst")
        sys.exit(0)

    # Write mode
    write_skills_json(generated, args.output)
    print(f"Written {len(skills)} skill(s) to {args.output}")
    for s in skills:
        print(f" - {s['workflow']} (from {s['source_file']})")


if __name__ == "__main__":
    main()
