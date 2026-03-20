#!/usr/bin/env bash
# Validates rule files in rules/ directories.
# Checks YAML frontmatter (title, impact, impactDescription, tags) and
# verifies at least one SQL code block exists.
#
# Usage:
#   validate-rules.sh                    # validate all rules in all skills
#   validate-rules.sh snowflake-best-practices  # validate specific skill's rules
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

errors=0
checked=0

check_rule() {
  local file="$1"
  local ok=true
  local filename
  filename="$(basename "$file")"

  # Skip template files
  if [[ "$filename" == _* ]]; then
    return
  fi

  ((checked++)) || true

  # Check YAML frontmatter exists (starts with ---)
  if ! head -1 "$file" | grep -q '^---$'; then
    echo "  FAIL: $file — missing YAML frontmatter"
    ok=false
  else
    # Check required frontmatter fields
    local frontmatter
    frontmatter=$(awk 'NR==1 && /^---$/{found=1; next} found && /^---$/{exit} found{print}' "$file")

    if ! echo "$frontmatter" | grep -q '^title:'; then
      echo "  FAIL: $file — missing 'title' in frontmatter"
      ok=false
    fi

    if ! echo "$frontmatter" | grep -q '^impact:'; then
      echo "  FAIL: $file — missing 'impact' in frontmatter"
      ok=false
    else
      # Validate impact level
      local impact
      impact=$(echo "$frontmatter" | grep '^impact:' | sed 's/^impact:[[:space:]]*//')
      if [[ "$impact" != "CRITICAL" && "$impact" != "HIGH" && "$impact" != "MEDIUM" ]]; then
        echo "  FAIL: $file — invalid impact '$impact' (must be CRITICAL, HIGH, or MEDIUM)"
        ok=false
      fi
    fi

    if ! echo "$frontmatter" | grep -q '^impactDescription:'; then
      echo "  FAIL: $file — missing 'impactDescription' in frontmatter"
      ok=false
    fi

    if ! echo "$frontmatter" | grep -q '^tags:'; then
      echo "  FAIL: $file — missing 'tags' in frontmatter"
      ok=false
    fi
  fi

  # Check for at least one SQL code block
  if ! grep -q '```sql' "$file"; then
    echo "  FAIL: $file — no SQL code blocks found"
    ok=false
  fi

  if ! $ok; then
    ((errors++)) || true
  fi
}

# ---------- determine which dirs to scan ----------

dirs=()
if [[ $# -gt 0 ]]; then
  dirs=("$@")
else
  # Find all directories containing a rules/ subdirectory
  for rules_dir in */rules/; do
    if [[ -d "$rules_dir" ]]; then
      dirs+=("$(dirname "$rules_dir")")
    fi
  done
fi

if [[ ${#dirs[@]} -eq 0 ]]; then
  echo "No rule directories to validate."
  exit 0
fi

for dir in "${dirs[@]}"; do
  rules_path="$dir/rules"
  if [[ ! -d "$rules_path" ]]; then
    echo "SKIP: $dir — no rules/ directory"
    continue
  fi

  echo "Checking rules in $rules_path ..."
  for file in "$rules_path"/*.md; do
    [[ -f "$file" ]] || continue
    check_rule "$file"
  done
done

echo ""
if [[ $errors -gt 0 ]]; then
  echo "FAILED: $errors rule(s) have issues out of $checked checked."
  exit 1
else
  echo "ALL PASSED: $checked rule(s) validated."
  exit 0
fi
