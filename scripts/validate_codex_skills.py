#!/usr/bin/env python3
"""Validate repository Codex skill frontmatter and skill-map coverage."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / "codex-skills"
SKILL_MAP = ROOT / "docs" / "SKILL_MAP.md"
NAME_RE = re.compile(r"^name:\s*([a-z0-9-]+)\s*$", re.MULTILINE)
DESCRIPTION_RE = re.compile(r"^description:\s*(.+?)\s*$", re.MULTILINE)


def main() -> int:
    problems: list[str] = []
    sources = sorted(SKILLS_ROOT.glob("*/SKILL.md"))
    if not sources:
        problems.append("No codex-skills/*/SKILL.md files were found.")

    try:
        skill_map = SKILL_MAP.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: cannot read {SKILL_MAP}: {exc}", file=sys.stderr)
        return 1

    for source in sources:
        text = source.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            problems.append(f"{source.relative_to(ROOT)}: missing YAML frontmatter.")
            continue
        _, frontmatter, _ = text.split("---", 2)
        name_match = NAME_RE.search(frontmatter)
        description_match = DESCRIPTION_RE.search(frontmatter)
        if name_match is None:
            problems.append(f"{source.relative_to(ROOT)}: missing lowercase skill name.")
            continue
        name = name_match.group(1)
        if name != source.parent.name:
            problems.append(
                f"{source.relative_to(ROOT)}: name '{name}' does not match folder."
            )
        if description_match is None or not description_match.group(1).strip().strip('"'):
            problems.append(f"{source.relative_to(ROOT)}: missing description.")
        if f"| {name} |" not in skill_map:
            problems.append(f"{source.relative_to(ROOT)}: '{name}' is absent from docs/SKILL_MAP.md.")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    print(f"Validated {len(sources)} Codex skills and their map entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
