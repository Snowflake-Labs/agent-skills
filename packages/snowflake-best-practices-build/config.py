"""Path configuration for the build tooling."""

from pathlib import Path

# Package root
PACKAGE_DIR = Path(__file__).parent

# Skill directory (relative to this package)
SKILL_DIR = PACKAGE_DIR.parent.parent / "snowflake-best-practices"
RULES_DIR = SKILL_DIR / "rules"
OUTPUT_FILE = SKILL_DIR / "AGENTS.md"

# Valid impact levels
VALID_IMPACTS = {"CRITICAL", "HIGH", "MEDIUM"}

# Category ordering for AGENTS.md build
CATEGORY_ORDER = [
    "warehouse",
    "cluster-key",
    "types",
    "query",
    "load",
    "semi",
    "cost",
]

# Map filename prefix to human-readable category name
CATEGORY_NAMES = {
    "warehouse": "Warehouse Configuration",
    "cluster-key": "Clustering Keys",
    "types": "Data Types",
    "query": "Query Optimization",
    "load": "Data Loading",
    "semi": "Semi-Structured Data",
    "cost": "Cost Control",
}
