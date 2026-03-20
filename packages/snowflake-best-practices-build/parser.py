"""Parse rule markdown files — extract YAML frontmatter and body content."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CodeExample:
    label: str
    code: str
    language: str = "sql"
    description: Optional[str] = None


@dataclass
class Rule:
    title: str
    impact: str
    impact_description: str
    tags: list[str]
    explanation: str
    examples: list[CodeExample] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    filename: str = ""
    category: str = ""


def _parse_tags(raw: str) -> list[str]:
    """Parse tags from YAML frontmatter, e.g. '[query, join, performance]'."""
    raw = raw.strip().strip("[]")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _infer_category(filename: str) -> str:
    """Infer category from filename prefix (e.g. 'warehouse-right-sizing' -> 'warehouse')."""
    name = Path(filename).stem
    # Handle multi-word prefixes like 'cluster-key'
    if name.startswith("cluster-key"):
        return "cluster-key"
    return name.split("-")[0]


def parse_rule_file(filepath: Path) -> Rule:
    """Parse a rule markdown file and return a Rule object."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    # --- Parse YAML frontmatter ---
    frontmatter: dict[str, str] = {}
    content_start = 0

    if lines[0].strip() == "---":
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                content_start = i + 1
                break
            if ":" in line:
                key, _, value = line.partition(":")
                frontmatter[key.strip()] = value.strip().strip('"').strip("'")

    # --- Parse body content ---
    body = "\n".join(lines[content_start:]).strip()

    # Extract explanation (text between the title heading and first example heading)
    explanation_lines: list[str] = []
    examples: list[CodeExample] = []
    references: list[str] = []

    current_example_label: Optional[str] = None
    current_example_desc: Optional[str] = None
    in_code_block = False
    code_block_lang = "sql"
    code_lines: list[str] = []
    in_explanation = True

    for line in body.split("\n"):
        # Skip the title heading
        if line.startswith("## ") and not examples and not current_example_label:
            continue

        # Skip impact line
        if line.startswith("**Impact:"):
            continue

        # Code block boundaries
        if line.startswith("```"):
            if in_code_block:
                # End code block
                if current_example_label:
                    examples.append(CodeExample(
                        label=current_example_label,
                        code="\n".join(code_lines),
                        language=code_block_lang,
                        description=current_example_desc,
                    ))
                    current_example_label = None
                    current_example_desc = None
                code_lines = []
                in_code_block = False
            else:
                # Start code block
                in_code_block = True
                code_block_lang = line[3:].strip() or "sql"
                code_lines = []
                in_explanation = False
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # Example labels: **Incorrect ...:** or **Correct ...:**
        label_match = re.match(r"^\*\*([^*]+)\*\*$", line.strip())
        if label_match:
            label_text = label_match.group(1).strip().rstrip(":")
            # Check if this looks like an example label
            example_keywords = (
                "incorrect", "correct", "bad", "good", "example",
                "also correct", "anti-pattern", "better",
            )
            if any(kw in label_text.lower() for kw in example_keywords):
                in_explanation = False
                # Parse label and optional description
                desc_match = re.match(r"^(.+?)\s*\((.+)\)$", label_text)
                if desc_match:
                    current_example_label = desc_match.group(1).strip()
                    current_example_desc = desc_match.group(2).strip()
                else:
                    current_example_label = label_text
                    current_example_desc = None
                continue

        # Reference links
        if line.startswith("Reference:") or line.startswith("References:"):
            ref_urls = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", line)
            references.extend(url for _, url in ref_urls)
            continue

        # Explanation text (before first example)
        if in_explanation and line.strip():
            explanation_lines.append(line)

    return Rule(
        title=frontmatter.get("title", ""),
        impact=frontmatter.get("impact", ""),
        impact_description=frontmatter.get("impactDescription", ""),
        tags=_parse_tags(frontmatter.get("tags", "")),
        explanation="\n".join(explanation_lines).strip(),
        examples=examples,
        references=references,
        filename=filepath.name,
        category=_infer_category(filepath.name),
    )
