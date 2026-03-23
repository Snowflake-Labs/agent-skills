# Contributing to Snowflake AI Kit

We welcome contributions from the community — new skills, builder app improvements, bug fixes, or documentation.

## Development Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/<your-username>/snowflake-ai-kit.git
   cd snowflake-ai-kit
   ```

2. Create a feature branch:
   ```bash
   git checkout -b add-my-skill
   ```

## Adding a New Skill

1. **Copy the template:**
   ```bash
   cp -r snowflake-skills/TEMPLATE snowflake-skills/my-skill-name
   ```

2. **Edit `SKILL.md`** — this is the agent-facing entry point:
   - Add YAML frontmatter with `name` and `description`
   - Include a `## When to Use` section (required by CI validation)
   - Write step-by-step instructions, patterns, and validation checks
   - Keep instructions actionable — the agent follows them literally

3. **Edit `README.md`** — this is the human-facing documentation:
   - Prerequisites and setup
   - Usage examples
   - Links to external docs

4. **Add supporting files** as needed:
   - `references/` — detailed guides, schemas, troubleshooting
   - `templates/` — code templates the agent can scaffold
   - `scripts/` — helper scripts the agent can execute

5. **Validate locally:**
   ```bash
   .github/scripts/validate-skill.sh snowflake-skills/my-skill-name
   ```

## Contributing to Builder Apps

Builder apps live under `builder-apps/`. Each app has its own README with setup instructions.

- **`builder-apps/claude-agent/`** — Claude Code agent with Snowflake MCP tools
- **`builder-apps/cortex-agent/`** — Cortex Agent chat UI

When contributing to builder apps:
- Follow the existing code patterns in the app you're modifying
- Test both backend and frontend changes from the browser (not just curl)
- Never commit credentials, `.env` files, or API keys
- Keep `projects/` directories out of version control (gitignored)

## Skill Standards

- **YAML frontmatter** — every `SKILL.md` must have `name` and `description`
- **`## When to Use` section** — required, tells the agent when to activate
- **No credentials** — never commit tokens, keys, `.env` files, or secrets
- **Self-contained** — each skill directory should work independently
- **Agent-agnostic** — skills are plain markdown, no proprietary format

## Code Standards

- Use lowercase with hyphens for directory names (e.g., `my-new-skill`)
- Include realistic, working code examples (no placeholders)
- Use environment variables for any credentials in examples

## Pull Request Process

1. Create a feature branch from `main`
2. Make changes with clear, descriptive commits
3. Run the validation script locally (for skills)
4. Open a PR with:
   - Brief description of the skill or change
   - Why it's useful
   - How you tested it
5. Address review feedback

The CI pipeline will automatically:
- Validate skill structure (`validate-skill.sh`)
- Check that the skills table in README.md is current

## Updating Existing Skills

When improving an existing skill:
- Keep backward compatibility in mind (don't break existing agent workflows)
- Update both `SKILL.md` and `README.md` if the change affects usage
- Test with at least one AI coding agent before submitting

## License

By submitting a contribution, you agree that your contributions will be licensed under the same terms as the project (Apache 2.0). See [LICENSE](LICENSE).
