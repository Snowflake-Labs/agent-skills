# snowflake-best-practices-build

Build and validation tooling for the `snowflake-best-practices` skill. Validates rule structure, compiles rules into `AGENTS.md`, and optionally checks SQL syntax against Snowflake.

## Scripts

| Script | Purpose |
|--------|---------|
| `validate.py` | Validate rule file structure (frontmatter, examples, impact levels) |
| `build.py` | Compile individual rule files into a single `AGENTS.md` |
| `validate_sql.py` | Optional SQL syntax check against Snowflake (requires credentials) |
| `verify_docs.py` | Check reference URLs and track fact freshness against Snowflake docs |

## Usage

```bash
cd packages/snowflake-best-practices-build

# Validate all rule files
python3 validate.py
python3 validate.py --verbose

# Build AGENTS.md from rules
python3 build.py
python3 build.py --check    # check if AGENTS.md is up to date
python3 build.py --stdout   # print to stdout

# Optional: validate SQL syntax (requires Snowflake credentials)
pip install -r requirements.txt
export SNOWFLAKE_ACCOUNT=... SNOWFLAKE_USER=... SNOWFLAKE_PASSWORD=...
python3 validate_sql.py
python3 validate_sql.py --skip-incorrect  # skip intentionally bad examples

# Verify documentation references and fact freshness
python3 verify_docs.py                    # structural checks
python3 verify_docs.py --check-urls       # also HTTP-check reference URLs
python3 verify_docs.py --stale-days 90    # warn if facts older than 90 days
python3 verify_docs.py --refresh          # mark all facts as verified (after manual review)
```

## CI Integration

The `.github/workflows/validate-pr.yml` workflow runs `validate.py` and checks `AGENTS.md` freshness on every PR that touches rule files.
