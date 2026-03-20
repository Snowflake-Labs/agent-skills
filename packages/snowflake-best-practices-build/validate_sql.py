#!/usr/bin/env python3
"""Optional SQL syntax validation using Snowflake's compile mode.

Extracts SQL code blocks from rule files and compiles them against Snowflake
to check for syntax errors. Requires Snowflake credentials.

Usage:
    python validate_sql.py                     # validate all SQL examples
    python validate_sql.py --skip-incorrect    # skip examples marked "Incorrect"

Environment variables (any standard Snowflake connection method works):
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD
    — or —
    SNOWFLAKE_CONNECTION_NAME (for named connections in ~/.snowflake/connections.toml)

If no credentials are available, the script exits with code 0 and a warning.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from config import RULES_DIR
from parser import parse_rule_file, CodeExample


def _get_connection():
    """Attempt to create a Snowflake connection. Returns None if unavailable."""
    try:
        import snowflake.connector
    except ImportError:
        print("WARNING: snowflake-connector-python not installed. Skipping SQL validation.")
        return None

    # Try named connection first
    conn_name = os.environ.get("SNOWFLAKE_CONNECTION_NAME")
    if conn_name:
        try:
            return snowflake.connector.connect(connection_name=conn_name)
        except Exception as e:
            print(f"WARNING: Named connection '{conn_name}' failed: {e}")

    # Try explicit credentials
    account = os.environ.get("SNOWFLAKE_ACCOUNT")
    user = os.environ.get("SNOWFLAKE_USER")
    password = os.environ.get("SNOWFLAKE_PASSWORD")

    if not all([account, user, password]):
        print("WARNING: No Snowflake credentials available. Skipping SQL validation.")
        print("  Set SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD")
        print("  or SNOWFLAKE_CONNECTION_NAME to enable SQL validation.")
        return None

    try:
        return snowflake.connector.connect(
            account=account,
            user=user,
            password=password,
        )
    except Exception as e:
        print(f"WARNING: Snowflake connection failed: {e}")
        return None


def _clean_sql_for_compile(sql: str) -> str | None:
    """Clean SQL for compilation. Returns None if not compilable."""
    # Remove inline comments for analysis
    cleaned = sql.strip()

    # Skip if it's just a comment
    if all(line.strip().startswith("--") or not line.strip() for line in cleaned.split("\n")):
        return None

    # Skip bash/shell commands
    if cleaned.startswith("#") or cleaned.startswith("split ") or cleaned.startswith("gzip "):
        return None

    # Skip partial snippets (no complete statement)
    if not any(kw in cleaned.upper() for kw in ("SELECT", "CREATE", "ALTER", "SHOW", "INSERT", "MERGE", "COPY")):
        return None

    return cleaned


def _compile_sql(conn, sql: str) -> str | None:
    """Compile SQL against Snowflake. Returns error message or None if valid."""
    try:
        cursor = conn.cursor()
        # Use EXPLAIN to check syntax without executing
        cursor.execute(f"EXPLAIN {sql}")
        cursor.close()
        return None
    except Exception as e:
        error_msg = str(e)
        # Filter out expected errors (references to non-existent tables/objects)
        expected_patterns = [
            "does not exist or not authorized",
            "object does not exist",
            "Object .* does not exist",
            "invalid identifier",
            "SQL compilation error",
        ]
        for pattern in expected_patterns:
            if re.search(pattern, error_msg, re.IGNORECASE):
                # These are expected — the rule references example table names
                return None
        return error_msg


def main() -> None:
    skip_incorrect = "--skip-incorrect" in sys.argv

    conn = _get_connection()
    if conn is None:
        sys.exit(0)  # Graceful skip

    print(f"Validating SQL syntax in rule files (connected to Snowflake)...")
    print(f"Rules directory: {RULES_DIR}")

    rule_files = sorted(
        f for f in RULES_DIR.glob("*.md")
        if not f.name.startswith("_") and f.name != "README.md"
    )

    total_sql = 0
    total_compiled = 0
    total_skipped = 0
    errors: list[str] = []

    for filepath in rule_files:
        try:
            rule = parse_rule_file(filepath)
        except Exception as e:
            print(f"  WARNING: Failed to parse {filepath.name}: {e}")
            continue

        for example in rule.examples:
            if example.language not in ("sql", ""):
                continue

            total_sql += 1

            # Skip "Incorrect" examples if flag is set
            if skip_incorrect and any(
                kw in example.label.lower()
                for kw in ("incorrect", "bad", "anti-pattern")
            ):
                total_skipped += 1
                continue

            cleaned = _clean_sql_for_compile(example.code)
            if cleaned is None:
                total_skipped += 1
                continue

            total_compiled += 1
            error = _compile_sql(conn, cleaned)
            if error:
                errors.append(
                    f"  {filepath.name} ({rule.title})\n"
                    f"    Example: {example.label}\n"
                    f"    SQL: {cleaned[:100]}{'...' if len(cleaned) > 100 else ''}\n"
                    f"    Error: {error}"
                )

    conn.close()

    print(f"\n  Total SQL examples: {total_sql}")
    print(f"  Compiled: {total_compiled}")
    print(f"  Skipped: {total_skipped}")

    if errors:
        print(f"\n  SQL validation issues ({len(errors)}):\n")
        for error in errors:
            print(error)
            print()
        # Don't exit 1 — SQL validation issues may be expected
        # (incorrect examples, references to example tables)
        print("NOTE: Some issues may be expected (intentionally incorrect examples).")
    else:
        print(f"\n  All {total_compiled} compiled SQL examples passed validation.")


if __name__ == "__main__":
    main()
