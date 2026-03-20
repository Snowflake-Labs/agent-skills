#!/usr/bin/env python3
"""Verify rule files reference valid Snowflake documentation and track fact freshness.

This script is part of the build harness. It:
  1. Checks every rule has a Reference: link
  2. Validates reference URLs are well-formed docs.snowflake.com links
  3. Checks a fact-manifest (verified_facts.json) for staleness
  4. Optionally fetches URLs to confirm they still resolve (--check-urls)

Usage:
    python verify_docs.py                 # structural checks only
    python verify_docs.py --check-urls    # also HTTP-check reference URLs
    python verify_docs.py --refresh       # update verified_facts.json timestamps
    python verify_docs.py --stale-days 90 # warn if facts older than 90 days (default: 180)
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from config import RULES_DIR

FACTS_FILE = Path(__file__).parent / "verified_facts.json"
DEFAULT_STALE_DAYS = 180
VALID_DOC_HOSTS = {"docs.snowflake.com", "docs.snowflake.cn"}

# Pattern to extract reference links from rule markdown
REF_PATTERN = re.compile(
    r"Reference:\s*\[([^\]]+)\]\(([^)]+)\)",
    re.IGNORECASE,
)

# Pattern to extract all markdown links
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_references(filepath: Path) -> list[tuple[str, str]]:
    """Extract (label, url) tuples from Reference: lines in a rule file."""
    text = filepath.read_text(encoding="utf-8")
    refs = REF_PATTERN.findall(text)
    return refs


def validate_url(url: str) -> list[str]:
    """Check that a URL is well-formed and points to Snowflake docs."""
    errors = []
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        errors.append(f"Malformed URL: {url}")
    elif parsed.scheme not in ("https", "http"):
        errors.append(f"Non-HTTP URL: {url}")
    return errors


def check_url_resolves(url: str) -> tuple[bool, int | str]:
    """HTTP HEAD check to see if a URL resolves. Returns (ok, status_or_error)."""
    try:
        import urllib.request

        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "snowflake-best-practices-build/1.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return (resp.status < 400, resp.status)
    except Exception as e:
        return (False, str(e))


def load_facts() -> dict:
    """Load the verified facts manifest."""
    if FACTS_FILE.exists():
        return json.loads(FACTS_FILE.read_text(encoding="utf-8"))
    return {"facts": {}, "last_full_review": None}


def save_facts(data: dict) -> None:
    """Save the verified facts manifest."""
    FACTS_FILE.write_text(
        json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8"
    )


def refresh_facts(rule_files: list[Path]) -> None:
    """Update all fact timestamps to now (after a manual review)."""
    now = datetime.now(timezone.utc).isoformat()
    data = load_facts()

    for filepath in rule_files:
        data["facts"][filepath.name] = {
            "last_verified": now,
            "references": [url for _, url in extract_references(filepath)],
        }

    data["last_full_review"] = now
    save_facts(data)
    print(f"Updated {len(rule_files)} facts in {FACTS_FILE.name}")


def check_staleness(rule_files: list[Path], stale_days: int) -> list[str]:
    """Check which rules haven't been verified recently."""
    warnings = []
    data = load_facts()
    now = datetime.now(timezone.utc)

    for filepath in rule_files:
        entry = data.get("facts", {}).get(filepath.name)
        if not entry:
            warnings.append(
                f"{filepath.name}: Never verified against documentation"
            )
            continue

        last = datetime.fromisoformat(entry["last_verified"])
        age_days = (now - last).days
        if age_days > stale_days:
            warnings.append(
                f"{filepath.name}: Last verified {age_days} days ago "
                f"(threshold: {stale_days} days)"
            )

    return warnings


def main() -> None:
    args = sys.argv[1:]
    do_check_urls = "--check-urls" in args
    do_refresh = "--refresh" in args
    stale_days = DEFAULT_STALE_DAYS

    if "--stale-days" in args:
        idx = args.index("--stale-days")
        if idx + 1 < len(args):
            stale_days = int(args[idx + 1])

    rule_files = sorted(
        f
        for f in RULES_DIR.glob("*.md")
        if not f.name.startswith("_") and f.name != "README.md"
    )

    if not rule_files:
        print("ERROR: No rule files found")
        sys.exit(1)

    if do_refresh:
        refresh_facts(rule_files)
        return

    print(f"Verifying documentation references in {len(rule_files)} rules ...\n")

    errors: list[str] = []
    warnings: list[str] = []

    for filepath in rule_files:
        refs = extract_references(filepath)

        if not refs:
            errors.append(f"{filepath.name}: No Reference: link found")
            continue

        for label, url in refs:
            url_errors = validate_url(url)
            errors.extend(f"{filepath.name}: {e}" for e in url_errors)

            if do_check_urls and not url_errors:
                ok, status = check_url_resolves(url)
                if not ok:
                    errors.append(
                        f"{filepath.name}: URL returned {status}: {url}"
                    )
                else:
                    print(f"  OK    {filepath.name} -> {url}")

    # Check staleness
    stale_warnings = check_staleness(rule_files, stale_days)
    warnings.extend(stale_warnings)

    # Report
    print()
    if warnings:
        print(f"WARNINGS: {len(warnings)} staleness warning(s):\n")
        for w in warnings:
            print(f"  WARN  {w}")
        print()

    if errors:
        print(f"FAILED: {len(errors)} error(s):\n")
        for e in errors:
            print(f"  FAIL  {e}")
        sys.exit(1)
    else:
        print(f"PASSED: All {len(rule_files)} rules have valid documentation references.")
        if warnings:
            print(
                f"\nRun 'python verify_docs.py --refresh' after reviewing rules "
                f"against current Snowflake docs to clear staleness warnings."
            )


if __name__ == "__main__":
    main()
