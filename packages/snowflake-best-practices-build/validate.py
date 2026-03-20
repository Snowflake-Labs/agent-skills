#!/usr/bin/env python3
"""Validate rule files have correct structure and frontmatter.

Usage:
    python validate.py                # validate all rules
    python validate.py --verbose      # show details for each rule
"""

from __future__ import annotations

import sys
from pathlib import Path

from config import RULES_DIR, VALID_IMPACTS
from parser import parse_rule_file


def validate_rule(filepath: Path, verbose: bool = False) -> list[str]:
    """Validate a single rule file. Returns list of error messages."""
    errors: list[str] = []
    filename = filepath.name

    try:
        rule = parse_rule_file(filepath)
    except Exception as e:
        return [f"{filename}: Failed to parse: {e}"]

    # Required frontmatter fields
    if not rule.title:
        errors.append(f"{filename}: Missing 'title' in frontmatter")

    if not rule.impact:
        errors.append(f"{filename}: Missing 'impact' in frontmatter")
    elif rule.impact not in VALID_IMPACTS:
        errors.append(
            f"{filename}: Invalid impact '{rule.impact}' "
            f"(must be one of: {', '.join(sorted(VALID_IMPACTS))})"
        )

    if not rule.impact_description:
        errors.append(f"{filename}: Missing 'impactDescription' in frontmatter")

    if not rule.tags:
        errors.append(f"{filename}: Missing or empty 'tags' in frontmatter")

    # Content checks
    if not rule.explanation:
        errors.append(f"{filename}: Missing explanation text")

    if not rule.examples:
        errors.append(f"{filename}: No code examples found")
    else:
        labels_lower = [e.label.lower() for e in rule.examples]
        has_incorrect = any(
            kw in label
            for label in labels_lower
            for kw in ("incorrect", "bad", "anti-pattern")
        )
        has_correct = any(
            kw in label
            for label in labels_lower
            for kw in ("correct", "good", "also correct", "better")
        )

        if not has_incorrect:
            errors.append(f"{filename}: Missing 'Incorrect' / 'Bad' example")
        if not has_correct:
            errors.append(f"{filename}: Missing 'Correct' / 'Good' example")

        # Check all examples have SQL code
        for example in rule.examples:
            if not example.code.strip():
                errors.append(
                    f"{filename}: Example '{example.label}' has empty code block"
                )

    if verbose and not errors:
        print(f"  PASS  {filename} ({rule.title})")

    return errors


def main() -> None:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    print(f"Validating rule files in {RULES_DIR} ...")

    rule_files = sorted(
        f for f in RULES_DIR.glob("*.md")
        if not f.name.startswith("_") and f.name != "README.md"
    )

    if not rule_files:
        print("ERROR: No rule files found")
        sys.exit(1)

    all_errors: list[str] = []

    for filepath in rule_files:
        errors = validate_rule(filepath, verbose=verbose)
        all_errors.extend(errors)

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) in {len(rule_files)} rule files:\n")
        for error in all_errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print(f"ALL PASSED: {len(rule_files)} rule files validated.")


if __name__ == "__main__":
    main()
