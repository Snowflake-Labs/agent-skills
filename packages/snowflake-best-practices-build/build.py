#!/usr/bin/env python3
"""Compile individual rule files into a single AGENTS.md document.

Usage:
    python build.py              # build AGENTS.md
    python build.py --check      # check if AGENTS.md is up to date (exit 1 if not)
    python build.py --stdout     # print to stdout instead of writing file
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from config import (
    CATEGORY_NAMES,
    CATEGORY_ORDER,
    OUTPUT_FILE,
    RULES_DIR,
)
from parser import Rule, parse_rule_file


def _load_rules() -> list[Rule]:
    """Load and parse all rule files."""
    rules: list[Rule] = []
    for filepath in sorted(RULES_DIR.glob("*.md")):
        if filepath.name.startswith("_") or filepath.name == "README.md":
            continue
        try:
            rules.append(parse_rule_file(filepath))
        except Exception as e:
            print(f"WARNING: Failed to parse {filepath.name}: {e}", file=sys.stderr)
    return rules


def _group_by_category(rules: list[Rule]) -> dict[str, list[Rule]]:
    """Group rules by category, maintaining CATEGORY_ORDER."""
    groups: dict[str, list[Rule]] = {}
    for rule in rules:
        cat = rule.category
        groups.setdefault(cat, []).append(rule)

    # Sort within each category by filename
    for cat in groups:
        groups[cat].sort(key=lambda r: r.filename)

    return groups


def build_agents_md(rules: list[Rule]) -> str:
    """Generate the AGENTS.md content from parsed rules."""
    groups = _group_by_category(rules)
    date = datetime.now(timezone.utc).strftime("%B %Y")

    lines: list[str] = []
    lines.append("# Snowflake Best Practices")
    lines.append("")
    lines.append(f"**{len(rules)} rules** | Generated {date}")
    lines.append("")
    lines.append("> **Note:**")
    lines.append("> This document is compiled from individual rule files in `rules/`.")
    lines.append("> It is designed for AI agents and LLMs to reference when designing,")
    lines.append("> optimizing, or maintaining Snowflake databases.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    section_num = 0
    for cat in CATEGORY_ORDER:
        if cat not in groups:
            continue
        section_num += 1
        cat_name = CATEGORY_NAMES.get(cat, cat.replace("-", " ").title())
        anchor = f"{section_num}-{cat_name.lower().replace(' ', '-')}"
        lines.append(f"{section_num}. [{cat_name}](#{anchor})")
        for i, rule in enumerate(groups[cat], 1):
            rule_anchor = f"{section_num}{i}-{rule.title.lower().replace(' ', '-')}"
            # Clean anchor
            rule_anchor = "".join(
                c for c in rule_anchor if c.isalnum() or c in "-"
            )
            lines.append(f"   - {section_num}.{i} {rule.title} — **{rule.impact}**")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections
    section_num = 0
    for cat in CATEGORY_ORDER:
        if cat not in groups:
            continue
        section_num += 1
        cat_name = CATEGORY_NAMES.get(cat, cat.replace("-", " ").title())
        lines.append(f"## {section_num}. {cat_name}")
        lines.append("")

        for i, rule in enumerate(groups[cat], 1):
            lines.append(f"### {section_num}.{i} {rule.title}")
            lines.append("")
            lines.append(
                f"**Impact: {rule.impact}**"
                + (f" ({rule.impact_description})" if rule.impact_description else "")
            )
            lines.append("")

            if rule.explanation:
                lines.append(rule.explanation)
                lines.append("")

            for example in rule.examples:
                label = example.label
                if example.description:
                    label += f" ({example.description})"
                lines.append(f"**{label}:**")
                lines.append("")
                lines.append(f"```{example.language}")
                lines.append(example.code)
                lines.append("```")
                lines.append("")

            if rule.references:
                refs = ", ".join(f"[{r}]({r})" for r in rule.references)
                lines.append(f"Reference: {refs}")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    check_mode = "--check" in sys.argv
    stdout_mode = "--stdout" in sys.argv

    rules = _load_rules()
    if not rules:
        print("ERROR: No rule files found", file=sys.stderr)
        sys.exit(1)

    content = build_agents_md(rules)

    if stdout_mode:
        print(content)
        return

    if check_mode:
        if OUTPUT_FILE.exists():
            existing = OUTPUT_FILE.read_text(encoding="utf-8")
            # Compare ignoring the generated date line
            def strip_date(text: str) -> str:
                return "\n".join(
                    line for line in text.split("\n")
                    if not line.startswith("**") or "Generated" not in line
                )
            if strip_date(existing) == strip_date(content):
                print(f"AGENTS.md is up to date ({len(rules)} rules)")
                return
        print("AGENTS.md is out of date. Run 'python build.py' to regenerate.")
        sys.exit(1)

    OUTPUT_FILE.write_text(content, encoding="utf-8")
    print(f"Built {OUTPUT_FILE} with {len(rules)} rules across {len(CATEGORY_ORDER)} categories")


if __name__ == "__main__":
    main()
