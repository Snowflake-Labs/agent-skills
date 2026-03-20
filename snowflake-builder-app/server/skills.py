"""Skills management for the Snowflake Builder App.

Copies skills from ../snowflake-skills/ into project directories so the
claude-agent-sdk can load them via .claude/skills/.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_SKILLS_DIR = Path(__file__).parent.parent.parent / "snowflake-skills"
APP_SKILLS_DIR = Path(__file__).parent.parent / "skills"


def discover_skills(enabled: list[str] | None = None) -> list[dict]:
    """Discover available skills from the snowflake-skills directory.

    Args:
        enabled: Optional list of skill folder names to include.
            If None, all skills with SKILL.md are included.

    Returns:
        List of dicts with skill name, path, and description.
    """
    skills = []

    if not REPO_SKILLS_DIR.exists():
        logger.warning(f"Skills directory not found: {REPO_SKILLS_DIR}")
        return skills

    for skill_dir in sorted(REPO_SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith(".") or skill_dir.name == "TEMPLATE":
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        if enabled and skill_dir.name not in enabled:
            continue

        skills.append({
            "name": skill_dir.name,
            "path": str(skill_dir),
            "has_skill_md": True,
        })

    return skills


def copy_skills_to_project(project_dir: Path, enabled: list[str] | None = None) -> int:
    """Copy skill files into a project's .claude/skills/ directory.

    Args:
        project_dir: The project root directory.
        enabled: Optional list of skill names to copy.

    Returns:
        Number of skills copied.
    """
    target_dir = project_dir / ".claude" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)

    skills = discover_skills(enabled)
    copied = 0

    for skill in skills:
        src = Path(skill["path"])
        dst = target_dir / skill["name"]

        if dst.exists():
            shutil.rmtree(dst)

        shutil.copytree(src, dst)
        copied += 1
        logger.info(f"Copied skill: {skill['name']} -> {dst}")

    return copied


def get_skills_summary(enabled: list[str] | None = None) -> str:
    """Get a formatted summary of available skills for the system prompt.

    Returns:
        Markdown-formatted skill list.
    """
    skills = discover_skills(enabled)
    if not skills:
        return "No Snowflake skills available."

    lines = ["Available Snowflake skills (use the Skill tool to load them):"]
    for skill in skills:
        lines.append(f"- **{skill['name']}**")

    return "\n".join(lines)
